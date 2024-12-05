import tkinter as tk
from tkinter import scrolledtext, messagebox
import threading
import json
import re
import logging
import queue
import requests
from typing import List

from clients.openai_client import OpenAIClient
from controllers.playwright_controller import PlaywrightController
from parsers.dom_parser import DOMParser
from utils.logger import setup_logging

class WebAgentGUI:
    def __init__(self, openai_client: OpenAIClient, playwright_controller: PlaywrightController):
        self.openai_client = openai_client
        self.playwright_controller = playwright_controller
        self.queue = queue.Queue()
        self.setup_logging()
        self.setup_gui()
        self.running = False

    def setup_logging(self):
        setup_logging()

    def setup_gui(self):
        self.root = tk.Tk()
        self.root.title("WebAgentAI")

        lbl = tk.Label(self.root, text="指示を入力してください:")
        lbl.pack(pady=10)

        self.txt_input = scrolledtext.ScrolledText(self.root, width=80, height=10)
        self.txt_input.pack(pady=10)

        # チャンク処理のチェックボックスを追加
        self.chunk_var = tk.BooleanVar(value=True)  # デフォルトでチャンクを有効にする
        chk_chunk = tk.Checkbutton(
            self.root,
            text="チャンク処理を有効にする",
            variable=self.chunk_var
        )
        chk_chunk.pack(pady=5)

        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=10)

        btn_execute_claude = tk.Button(btn_frame, text="Claudeで実行", command=lambda: self.on_execute("Claude"))
        btn_execute_claude.pack(side=tk.LEFT, padx=10)

        btn_execute_gpt4o = tk.Button(btn_frame, text="GPT4oで実行", command=lambda: self.on_execute("GPT4o"))
        btn_execute_gpt4o.pack(side=tk.LEFT, padx=10)

        lbl_actions = tk.Label(self.root, text="実行中の操作:")
        lbl_actions.pack(pady=10)

        self.txt_actions = scrolledtext.ScrolledText(
            self.root, width=80, height=20, state=tk.DISABLED, font=("Helvetica", 12)
        )
        self.txt_actions.pack(pady=10)

        btn_save = tk.Button(self.root, text="保存", command=self.save_actions)
        btn_save.pack(pady=10)

        self.root.after(100, self.process_queue)

    def validate_user_instruction(self, user_instruction: str) -> (bool, str):
        if not user_instruction:
            return False, "プロンプトが空です。"
        if not re.search(r'https?://\S+', user_instruction):
            return False, "有効なURLが含まれていません。"
        return True, ""

    def set_widget_state(self, widget, state):
        try:
            widget.config(state=state)
        except tk.TclError:
            pass

    def on_execute(self, model: str):
        user_instruction = self.txt_input.get("1.0", tk.END).strip()
        is_valid, message = self.validate_user_instruction(user_instruction)
        if not is_valid:
            messagebox.showwarning("入力エラー", message)
            return

        for widget in self.root.winfo_children():
            self.set_widget_state(widget, tk.DISABLED)

        self.txt_actions.config(state=tk.NORMAL)
        self.txt_actions.delete("1.0", tk.END)
        self.txt_actions.config(state=tk.DISABLED)

        self.running = True

        # チャンクフラグを取得
        chunking_enabled = self.chunk_var.get()

        threading.Thread(
            target=self.run_execution, args=(model, user_instruction, chunking_enabled), daemon=True
        ).start()

    def run_execution(self, model: str, user_instruction: str, chunking_enabled: bool):
        try:
            logging.info(f"ユーザー指示の実行を開始しました。モデル: {model}")
            actions, raw_response = self.process_instruction(model, user_instruction, chunking_enabled)
            if not actions:
                messagebox.showerror("エラー", "アクションの生成に失敗しました。ログを確認してください。")
                return
            self.queue.put(("add_actions", actions))
            self.playwright_controller.perform_actions(
                actions, self.extract_url(user_instruction), self.action_callback
            )
            messagebox.showinfo("完了", "操作が完了しました。")
            logging.info("ユーザー指示の実行が完了しました。")
        except Exception as e:
            logging.error(f"実行中にエラーが発生しました: {e}")
            messagebox.showerror("エラー", f"実行中にエラーが発生しました: {e}")
        finally:
            self.running = False
            self.root.after(0, lambda: self.enable_widgets())

    def enable_widgets(self):
        for widget in self.root.winfo_children():
            self.set_widget_state(widget, tk.NORMAL)

    def extract_url(self, user_instruction: str) -> str:
        url_match = re.search(r'https?://\S+', user_instruction)
        return url_match.group() if url_match else ""

    def process_instruction(self, model: str, user_instruction: str, chunking_enabled: bool):
        url = self.extract_url(user_instruction)
        task = user_instruction.replace(url, "") if url else user_instruction

        dom_elements = []
        if url:
            logging.info(f"指定されたURLからHTMLコンテンツを取得します: {url}")
            try:
                response = requests.get(url, timeout=60)
                response.raise_for_status()
                html_content = response.text
                logging.info("HTMLコンテンツの取得に成功しました。")
            except requests.exceptions.Timeout:
                logging.error(f"タイムアウトエラー: URL '{url}' のページをロードできませんでした。")
                return [], ""
            except requests.exceptions.RequestException as e:
                logging.error(f"HTMLコンテンツの取得に失敗しました: {e}")
                return [], ""

            dom_elements = DOMParser.parse(html_content or "")
            
            if chunking_enabled:
                chunks = self.chunk_dom_elements(dom_elements, max_chunk_size=100000)
            else:
                chunks = [dom_elements]  # チャンク処理を無効にする場合、全体を一つのチャンクとして扱う

            all_actions = []
            for i, chunk in enumerate(chunks, start=1):
                logging.info(f"チャンク {i} を処理しています。")
                actions, raw_response = self.openai_client.generate_actions(model, task, chunk)
                if actions:
                    all_actions.extend(actions)
                else:
                    logging.warning(f"チャンク {i} でアクションの生成に失敗しました。")

            if not all_actions:
                logging.error("すべてのチャンクでアクションの生成に失敗しました。")
                return [], ""

            logging.info(f"全チャンクから生成されたアクションの総数: {len(all_actions)}")
            return all_actions, ""
        else:
            actions, raw_response = self.openai_client.generate_actions(model, task, dom_elements)
            if raw_response:
                logging.debug(f"APIからの生のレスポンス: {raw_response}")
            logging.info(f"生成されたアクション: {actions}")
            return actions, raw_response

    def action_callback(self, index, action, selector, value, code_snippet='', success=True):
        if success:
            status = "完了"
            self.queue.put((index, status, code_snippet))
            logging.debug(f"アクション {index}: {action} - {status} - {code_snippet}")
        else:
            status = "失敗"
            self.queue.put((index, status, "不明なエラー"))
            logging.debug(f"アクション {index}: {action} - {status} - 不明なエラー")

    def process_queue(self):
        try:
            while True:
                message = self.queue.get_nowait()
                if isinstance(message, tuple):
                    if message[0] == "add_actions":
                        actions = message[1]
                        self.add_actions_to_list(actions)
                    elif len(message) == 3:
                        index, status, info = message
                        self.update_action_status(index, status, info)
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.process_queue)

    def add_actions_to_list(self, actions: List[dict]):
        logging.debug("add_actions_to_list が呼び出されました。")
        self.txt_actions.config(state=tk.NORMAL)
        for index, action in enumerate(actions, start=1):
            act = action.get("action")
            sel = action.get("selector")
            val = action.get("value")
            action_text = f"{index}. {act} - Selector: {sel}, Value: {val}"
            self.txt_actions.insert(tk.END, action_text + "\n")
        self.txt_actions.config(state=tk.DISABLED)
        self.txt_actions.see(tk.END)
        logging.debug("操作リストにアクションが追加されました。")

    def update_action_status(self, index: int, status: str, info: str = None):
        logging.debug(f"update_action_status が呼び出されました。ステップ: {index}, ステータス: {status}, 情報: {info}")
        self.txt_actions.config(state=tk.NORMAL)

        line_start_pos = f"{index}.0"
        line_end_pos = f"{index}.end"

        if status == "完了":
            tag_name = f"completed_{index}"
            self.txt_actions.tag_config(tag_name, foreground="green")
            action_text = f"{index}. 完了: {info}"
        else:
            tag_name = f"failed_{index}"
            self.txt_actions.tag_config(tag_name, foreground="red")
            action_text = f"{index}. 失敗: {info or '不明なエラー'}"

        self.txt_actions.delete(f"{index}.0", f"{index}.end")
        self.txt_actions.insert(f"{index}.0", action_text + "\n")
        self.txt_actions.tag_add(tag_name, line_start_pos, f"{index}.end")

        self.txt_actions.config(state=tk.DISABLED)
        logging.debug(f"ステップ {index} が {status} に色付けされました。")

    def save_actions(self):
        actions_text = self.txt_actions.get("1.0", tk.END).strip()
        if actions_text:
            try:
                with open("actions_log.txt", "w", encoding="utf-8") as f:
                    f.write(actions_text)
                messagebox.showinfo("保存完了", "操作リストを保存しました。")
            except Exception as e:
                logging.error(f"操作リストの保存に失敗しました: {e}")
                messagebox.showerror("エラー", f"操作リストの保存に失敗しました: {e}")
        else:
            messagebox.showwarning("警告", "保存する操作リストがありません。")

    def start(self):
        self.root.mainloop()

    def chunk_dom_elements(self, dom_elements: list, max_chunk_size: int = 10000) -> list:
        chunks = []
        current_chunk = []
        current_size = 0

        for element in dom_elements:
            element_str = json.dumps(element, ensure_ascii=False)
            element_size = len(element_str)
            if current_size + element_size > max_chunk_size:
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = []
                    current_size = 0
            current_chunk.append(element)
            current_size += element_size

        if current_chunk:
            chunks.append(current_chunk)

        logging.info(f"dom_elementsを{len(chunks)}チャンクに分割しました。")
        return chunks
