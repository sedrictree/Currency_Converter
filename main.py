import tkinter as tk
from tkinter import ttk, messagebox
import requests
import json
import os
from datetime import datetime

API_URL = "https://www.cbr-xml-daily.ru/daily_json.js"
HISTORY_FILE = "history.json"
CURRENCIES = ["RUB", "USD", "EUR", "CNY", "KZT", "GBP", "JPY", "TRY"]


class DataManager:
    """Работа с API и файлом истории"""
    def __init__(self):
        self.rates = {}

    def fetch_rates(self):
        try:
            response = requests.get(API_URL, timeout=10)
            response.raise_for_status()
            data = response.json()
            self.rates = {"RUB": 1.0}
            for code, info in data["Valute"].items():
                self.rates[code] = info["Value"] / info["Nominal"]
            return True
        except Exception as e:
            print(f"Ошибка API: {e}")
            return False

    def convert(self, amount, from_curr, to_curr):
        if from_curr not in self.rates or to_curr not in self.rates:
            return None
        return amount * self.rates[from_curr] / self.rates[to_curr]

    def load_history(self):
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def save_history(self, history):
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)


class CurrencyApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Конвертер валют")
        self.root.geometry("550x500")

        self.data = DataManager()
        self.history = []

        self.build_ui()
        self.load_data()

    def build_ui(self):
        # Статус и обновление
        top_frame = tk.Frame(self.root, padx=10, pady=5)
        top_frame.pack(fill=tk.X)

        self.lbl_status = tk.Label(top_frame, text="Загрузка курсов...")
        self.lbl_status.pack(side=tk.LEFT)

        self.btn_refresh = tk.Button(top_frame, text="Обновить курсы", command=self.refresh_rates)
        self.btn_refresh.pack(side=tk.RIGHT)

        # Разделитель
        tk.Frame(self.root, height=2, bd=1, relief=tk.SUNKEN).pack(fill=tk.X, padx=5, pady=5)

        # Панель ввода
        input_frame = tk.LabelFrame(self.root, text="Конвертация", padx=10, pady=10)
        input_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(input_frame, text="Сумма:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.entry_amount = tk.Entry(input_frame, width=15)
        self.entry_amount.grid(row=0, column=1, sticky=tk.W, padx=5)
        self.entry_amount.bind("<Return>", lambda e: self.do_convert())

        tk.Label(input_frame, text="Из:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.combo_from = ttk.Combobox(input_frame, values=CURRENCIES, state="readonly", width=10)
        self.combo_from.grid(row=1, column=1, sticky=tk.W, padx=5)
        self.combo_from.set("USD")

        tk.Label(input_frame, text="В:").grid(row=1, column=2, sticky=tk.W, padx=15)
        self.combo_to = ttk.Combobox(input_frame, values=CURRENCIES, state="readonly", width=10)
        self.combo_to.grid(row=1, column=3, sticky=tk.W, padx=5)
        self.combo_to.set("RUB")

        btn_frame = tk.Frame(input_frame)
        btn_frame.grid(row=2, column=0, columnspan=4, pady=10)

        self.btn_convert = tk.Button(btn_frame, text="Конвертировать", command=self.do_convert)
        self.btn_convert.pack(side=tk.LEFT, padx=5)

        self.lbl_result = tk.Label(btn_frame, text="Результат: -")
        self.lbl_result.pack(side=tk.LEFT, padx=15)

        # Разделитель
        tk.Frame(self.root, height=2, bd=1, relief=tk.SUNKEN).pack(fill=tk.X, padx=5, pady=5)

        # Таблица истории
        hist_frame = tk.LabelFrame(self.root, text="История операций", padx=10, pady=10)
        hist_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        cols = ("time", "from_c", "to_c", "amount", "result", "rate")
        self.tree = ttk.Treeview(hist_frame, columns=cols, show="headings", height=6)
        self.tree.heading("time", text="Время")
        self.tree.heading("from_c", text="Из")
        self.tree.heading("to_c", text="В")
        self.tree.heading("amount", text="Сумма")
        self.tree.heading("result", text="Результат")
        self.tree.heading("rate", text="Курс")

        for col in cols:
            self.tree.column(col, anchor=tk.CENTER, width=80)

        scrollbar = ttk.Scrollbar(hist_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        hist_btn_frame = tk.Frame(hist_frame)
        hist_btn_frame.pack(fill=tk.X, pady=(5, 0))

        tk.Button(hist_btn_frame, text="Очистить историю", command=self.clear_history).pack(side=tk.LEFT)
        tk.Button(hist_btn_frame, text="Экспорт JSON", command=self.export_history).pack(side=tk.RIGHT)

    def load_data(self):
        self.refresh_rates()
        self.history = self.data.load_history()
        self.update_table()

    def refresh_rates(self):
        self.btn_refresh.config(state="disabled")
        self.lbl_status.config(text="Загрузка...")
        self.root.update()
        if self.data.fetch_rates():
            self.lbl_status.config(text="Курсы обновлены")
        else:
            self.lbl_status.config(text="Ошибка загрузки")
        self.btn_refresh.config(state="normal")

    def do_convert(self):
        raw = self.entry_amount.get().strip()
        try:
            amount = float(raw)
            if amount <= 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Ошибка ввода", "Введите положительное число!")
            return

        if not self.data.rates:
            messagebox.showwarning("Нет данных", "Обновите курсы валют!")
            return

        from_c = self.combo_from.get()
        to_c = self.combo_to.get()
        result = self.data.convert(amount, from_c, to_c)

        if result is None:
            messagebox.showerror("Ошибка", "Неизвестная валюта")
            return

        rate = result / amount
        self.lbl_result.config(text=f"Результат: {result:.2f} {to_c}")

        record = {
            "time": datetime.now().strftime("%H:%M:%S"),
            "from": from_c,
            "to": to_c,
            "amount": amount,
            "result": round(result, 2),
            "rate": round(rate, 4)
        }
        self.history.insert(0, record)
        self.data.save_history(self.history)
        self.update_table()

    def update_table(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for r in self.history:
            self.tree.insert("", tk.END, values=(
                r["time"], r["from"], r["to"],
                f"{r['amount']:.2f}", f"{r['result']:.2f}", f"{r['rate']:.4f}"
            ))

    def clear_history(self):
        if messagebox.askyesno("Подтверждение", "Удалить историю?"):
            self.history = []
            self.data.save_history(self.history)
            self.update_table()

    def export_history(self):
        filename = f"history_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
            messagebox.showinfo("Готово", f"Сохранено в {filename}")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))


if __name__ == "__main__":
    try:
        import requests
    except ImportError:
        print("Установите библиотеку: pip install requests")
        exit(1)

    root = tk.Tk()
    app = CurrencyApp(root)
    root.mainloop()