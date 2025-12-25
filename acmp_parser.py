from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from openai import OpenAI
import time
import re
import warnings
<<<<<<< HEAD
import json
import os
from datetime import datetime

=======

# Отключаем предупреждения SSL
>>>>>>> 2e5d7d31b57a90bcd1afa1b4b497613429e909bc
warnings.filterwarnings("ignore", category=DeprecationWarning)


class ACMPSolverBrowser:
    def __init__(self, openrouter_api_key=None, site_url="https://acmp.ru", site_name="ACMP Solver"):
        self.openrouter_api_key = openrouter_api_key
        self.site_url = site_url
        self.site_name = site_name
<<<<<<< HEAD
        self.solutions_file = "solutions_history.json"
        self.best_solutions_file = "best_solutions.json"
        
        # Загружаем историю решений
        self.solutions_history = self.load_solutions_history()
        self.best_solutions = self.load_best_solutions()
        
=======

        # Инициализация OpenAI-совместимого клиента для OpenRouter
>>>>>>> 2e5d7d31b57a90bcd1afa1b4b497613429e909bc
        if openrouter_api_key:
            self.client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=openrouter_api_key,
            )
        else:
            self.client = None

<<<<<<< HEAD
=======
        # Настройка браузера
>>>>>>> 2e5d7d31b57a90bcd1afa1b4b497613429e909bc
        chrome_options = Options()
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-infobars")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("--ignore-certificate-errors")
        chrome_options.add_argument("--ignore-ssl-errors")

        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 20)

<<<<<<< HEAD
    def load_solutions_history(self):
        """Загружаем историю решений из JSON файла"""
        if os.path.exists(self.solutions_file):
            try:
                with open(self.solutions_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def load_best_solutions(self):
        """Загружаем лучшие решения из JSON файла"""
        if os.path.exists(self.best_solutions_file):
            try:
                with open(self.best_solutions_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_solutions_history(self):
        """Сохраняем историю решений в JSON файл"""
        try:
            with open(self.solutions_file, 'w', encoding='utf-8') as f:
                json.dump(self.solutions_history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения истории решений: {e}")

    def save_best_solutions(self):
        """Сохраняем лучшие решения в JSON файл"""
        try:
            with open(self.best_solutions_file, 'w', encoding='utf-8') as f:
                json.dump(self.best_solutions, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения лучших решений: {e}")

    def add_solution_to_history(self, task_id, solution_code, attempt_number, status, result_text=""):
        """Добавляем решение в историю"""
        if str(task_id) not in self.solutions_history:
            self.solutions_history[str(task_id)] = []
        
        solution_entry = {
            "timestamp": datetime.now().isoformat(),
            "attempt": attempt_number,
            "code": solution_code,
            "status": status,
            "result": result_text,
            "is_accepted": status == "Accepted"
        }
        
        self.solutions_history[str(task_id)].append(solution_entry)
        self.save_solutions_history()
        
        # Проверяем, является ли это решение лучшим (Accepted)
        if status == "Accepted":
            self.update_best_solution(task_id, solution_code, solution_entry)

    def update_best_solution(self, task_id, solution_code, solution_entry):
        """Обновляем лучшее решение для задачи"""
        task_id_str = str(task_id)
        
        if task_id_str not in self.best_solutions:
            self.best_solutions[task_id_str] = solution_entry
            self.save_best_solutions()
            return
        
        # Проверяем, нужно ли обновить лучшее решение
        current_best = self.best_solutions[task_id_str]
        current_time = datetime.fromisoformat(current_best["timestamp"])
        new_time = datetime.fromisoformat(solution_entry["timestamp"])
        
        # Если новое решение принято и оно более новое, обновляем
        if solution_entry["is_accepted"] and new_time > current_time:
            self.best_solutions[task_id_str] = solution_entry
            self.save_best_solutions()

    def get_previous_solutions_prompt(self, task_id):
        """Формируем промт с предыдущими решениями"""
        task_id_str = str(task_id)
        prompt_parts = []
        
        # Добавляем лучшие решения из других задач
        if self.best_solutions:
            prompt_parts.append("УЧАСТКИ КОДА ИЗ ДРУГИХ РЕШЕННЫХ ЗАДАЧ:")
            for other_task_id, solution_data in self.best_solutions.items():
                if other_task_id != task_id_str and len(solution_data.get("code", "")) < 500:
                    prompt_parts.append(f"Задача {other_task_id} (Accepted):")
                    prompt_parts.append(f"```python\n{solution_data.get('code', '')}\n```\n")
        
        # Добавляем предыдущие попытки для текущей задачи
        if task_id_str in self.solutions_history:
            attempts = self.solutions_history[task_id_str]
            if attempts:
                prompt_parts.append(f"\nПРЕДЫДУЩИЕ ПОПЫТКИ ДЛЯ ЗАДАЧИ {task_id}:")
                for attempt in attempts[-3:]:  # Последние 3 попытки
                    status = attempt.get("status", "Unknown")
                    result = attempt.get("result", "")
                    prompt_parts.append(f"Попытка {attempt.get('attempt', '?')} - {status}: {result}")
                    prompt_parts.append(f"Код:\n```python\n{attempt.get('code', '')}\n```\n")
        
        return "\n".join(prompt_parts) if prompt_parts else ""

    def ask_ai(self, prompt, task_id):
        if not self.client or not self.openrouter_api_key:
            # Получаем предыдущие решения для промта
            previous_solutions_prompt = self.get_previous_solutions_prompt(task_id)
            
            # Добавляем в основной промт
            full_prompt = f"{prompt}\n\n{previous_solutions_prompt}"
            
=======
    def ask_ai(self, prompt):
        """Запрос к нейросети через OpenRouter"""
        if not self.client or not self.openrouter_api_key:
>>>>>>> 2e5d7d31b57a90bcd1afa1b4b497613429e909bc
            demo_solutions = {
                "1": "a, b = map(int, input().split())\nprint(a + b)",
                "2": "n = int(input())\nprint(n)",
                "3": "n = int(input())\nprint(n + 1)",
                "100": "print(sum(map(int, input().split())))",
                "200": "n = int(input())\nprint(n * n)",
                "500": "print(input().upper())",
                "1000": "print('Hello, World!')"
            }

<<<<<<< HEAD
            for task_id_key, solution in demo_solutions.items():
                if f"id_task={task_id_key}" in prompt or f"Задача {task_id_key}" in prompt:
                    return f"```python\n{solution}\n```"

            return f"""```python
# Универсальное решение с учетом предыдущих попыток
{previous_solutions_prompt if previous_solutions_prompt else ''}
import sys
data = sys.stdin.read().strip()
if data:
    print(data)
else:
    print('0')
```"""

        try:
            # Получаем предыдущие решения для промта
            previous_solutions_prompt = self.get_previous_solutions_prompt(task_id)
            
            # Формируем полный промт с историей решений
            full_prompt = f"""{prompt}

ИСТОРИЯ РЕШЕНИЙ:
{previous_solutions_prompt}

ПРОАНАЛИЗИРУЙ ПРЕДЫДУЩИЕ ПОПЫТКИ И ПРЕДЛОЖИ УЛУЧШЕННОЕ РЕШЕНИЕ."""
            
=======
            for task_id, solution in demo_solutions.items():
                if f"id_task={task_id}" in prompt or f"Задача {task_id}" in prompt:
                    return f"```python\n{solution}\n```"

            return "```python\n# Универсальное решение\nimport sys\ndata = sys.stdin.read().strip()\nif data:\n    print(data)\nelse:\n    print('0')\n```"

        try:
>>>>>>> 2e5d7d31b57a90bcd1afa1b4b497613429e909bc
            completion = self.client.chat.completions.create(
                extra_headers={
                    "HTTP-Referer": self.site_url,
                    "X-Title": self.site_name,
                },
                model="kwaipilot/kat-coder-pro:free",
                messages=[
                    {
                        "role": "system",
<<<<<<< HEAD
                        "content": """Ты - эксперт по программированию и решению олимпиадных задач. 
                        Ты видишь предыдущие попытки решения этой и других задач. 
                        Анализируй ошибки предыдущих решений и предлагай улучшенный код.
                        Пиши чистый, эффективный код на Python. 
                        Код должен читать из input() и выводить через print()."""
                    },
                    {
                        "role": "user",
                        "content": full_prompt
=======
                        "content": "Ты - эксперт по программированию и решению олимпиадных задач. Пиши чистый, эффективный код на Python. Код должен читать из input() и выводить через print()."
                    },
                    {
                        "role": "user",
                        "content": prompt
>>>>>>> 2e5d7d31b57a90bcd1afa1b4b497613429e909bc
                    }
                ],
            )
            return completion.choices[0].message.content
        except Exception as e:
<<<<<<< HEAD
            print(f"Ошибка API: {e}")
            return f"```python\n# Ошибка API, базовое решение\nprint(input())\n```"

    def wait_for_authorization(self):
=======
            return f"```python\n# Ошибка API, базовое решение\nprint(input())\n```"

    def wait_for_authorization(self):
        """Ожидание завершения авторизации пользователем"""
>>>>>>> 2e5d7d31b57a90bcd1afa1b4b497613429e909bc
        print("Ожидаем авторизации...")
        max_wait_time = 300
        start_time = time.time()

        while time.time() - start_time < max_wait_time:
            try:
<<<<<<< HEAD
                user_elements = self.driver.find_elements(By.XPATH,
                                                          "//*[contains(text(), 'Выход') or contains(text(), 'Logout') or contains(@href, 'logout')]")

=======
                # Проверяем различные элементы, указывающие на авторизацию
                user_elements = self.driver.find_elements(By.XPATH,
                                                          "//*[contains(text(), 'Выход') or contains(text(), 'Logout') or contains(@href, 'logout')]")

                # Также проверяем наличие меню пользователя
>>>>>>> 2e5d7d31b57a90bcd1afa1b4b497613429e909bc
                user_menu = self.driver.find_elements(By.XPATH, "//a[contains(@href, 'main=user')]")

                if user_elements or user_menu:
                    print("Авторизация обнаружена!")
<<<<<<< HEAD
                    time.sleep(3)
                    return True

=======
                    # Даем время для полной загрузки страницы после авторизации
                    time.sleep(3)
                    return True

                # Проверяем, не появилась ли страница с ошибкой
>>>>>>> 2e5d7d31b57a90bcd1afa1b4b497613429e909bc
                if "error" in self.driver.current_url.lower() or "ошибка" in self.driver.page_source.lower():
                    print("Обнаружена ошибка страницы, перезагружаем...")
                    self.driver.get("https://acmp.ru/index.asp?main=tasks")

                time.sleep(5)
            except Exception as e:
                print(f"Ошибка при проверке авторизации: {e}")
                time.sleep(5)

        print("Превышено время ожидания авторизации")
        return False

    def get_all_task_urls(self):
<<<<<<< HEAD
        task_urls = []
        for task_id in range(555, 1001):
=======
        """Получение ссылок на все задачи с 1 по 1000"""
        task_urls = []
        for task_id in range(418, 1001):
>>>>>>> 2e5d7d31b57a90bcd1afa1b4b497613429e909bc
            task_url = f"https://acmp.ru/index.asp?main=task&id_task={task_id}"
            task_urls.append(task_url)
        return task_urls

    def parse_task_page(self):
        """Парсинг страницы задачи"""
        try:
            title = self.driver.find_element(By.TAG_NAME, "h1").text
        except:
            title = "Неизвестная задача"

        description = ""
        try:
            meta_desc = self.driver.find_element(By.XPATH, "//meta[@name='description']")
            description = meta_desc.get_attribute("content")
        except:
            pass

        full_text = ""
        try:
            content_div = self.driver.find_element(By.XPATH, "//td[contains(@background, 'notepad2.gif')]")
            paragraphs = content_div.find_elements(By.TAG_NAME, "p")
            for p in paragraphs:
                if p.text.strip():
                    full_text += p.text.strip() + "\n"
        except:
            pass

        input_data = ""
        try:
            input_header = self.driver.find_element(By.XPATH, "//h2[contains(text(), 'Входные данные')]")
            next_element = input_header.find_element(By.XPATH, "./following-sibling::*[1]")
            input_elements = []
            while next_element and next_element.tag_name != 'h2':
                if next_element.text.strip():
                    input_elements.append(next_element.text.strip())
                try:
                    next_element = next_element.find_element(By.XPATH, "./following-sibling::*[1]")
                except:
                    break
            input_data = "\n".join(input_elements)
        except:
            pass

        output_data = ""
        try:
            output_header = self.driver.find_element(By.XPATH, "//h2[contains(text(), 'Выходные данные')]")
            next_element = output_header.find_element(By.XPATH, "./following-sibling::*[1]")
            output_elements = []
            while next_element and next_element.tag_name != 'h2' and next_element.tag_name != 'table':
                if next_element.text.strip():
                    output_elements.append(next_element.text.strip())
                try:
                    next_element = next_element.find_element(By.XPATH, "./following-sibling::*[1]")
                except:
                    break
            output_data = "\n".join(output_elements)
        except:
            pass

        examples = ""
        try:
            example_table = self.driver.find_element(By.XPATH,
                                                     "//table[.//th[contains(text(), 'INPUT.TXT') or contains(text(), 'OUTPUT.TXT')]]")
            examples = example_table.text
        except:
            pass

        complete_description = f"""{description}

{full_text}

ВХОДНЫЕ ДАННЫЕ:
{input_data}

ВЫХОДНЫЕ ДАННЫЕ:
{output_data}

ПРИМЕРЫ:
{examples}"""

        return {
            'title': title,
            'description': complete_description[:1500] + "..." if len(
                complete_description) > 1500 else complete_description,
            'full_description': complete_description,
            'input_data': input_data,
            'output_data': output_data,
            'examples': examples
        }

    def set_code_in_codemirror(self, code):
<<<<<<< HEAD
=======
        """Ввод кода в CodeMirror редактор"""
>>>>>>> 2e5d7d31b57a90bcd1afa1b4b497613429e909bc
        try:
            escaped_code = code.replace('`', '\\`').replace('${', '\\${')
            js_script = f"""
            var editor = document.querySelector('.CodeMirror').CodeMirror;
            if (editor) {{
                editor.setValue(`{escaped_code}`);
                return true;
            }}
            return false;
            """
            result = self.driver.execute_script(js_script)
            return result is not False
        except Exception as e:
            print(f"Ошибка ввода кода: {e}")
            return False

    def select_language(self, lang="PY"):
<<<<<<< HEAD
=======
        """Выбор языка программирования"""
>>>>>>> 2e5d7d31b57a90bcd1afa1b4b497613429e909bc
        try:
            lang_select = self.driver.find_element(By.NAME, "lang")
            js_script = f"""
            var select = arguments[0];
            select.value = '{lang}';
            var event = new Event('change', {{ bubbles: true }});
            select.dispatchEvent(event);
            return true;
            """
            result = self.driver.execute_script(js_script, lang_select)
            return result is not False
        except Exception as e:
            print(f"Ошибка выбора языка: {e}")
            return False

    def submit_solution(self, solution_code):
<<<<<<< HEAD
        try:
=======
        """Отправка решения через браузер"""
        try:
            # Ждем загрузки формы
>>>>>>> 2e5d7d31b57a90bcd1afa1b4b497613429e909bc
            form = self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "form")))
            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", form)
            time.sleep(1)

            if not self.set_code_in_codemirror(solution_code):
                return False

            if not self.select_language("PY"):
                return False

<<<<<<< HEAD
=======
            # Ждем доступности кнопки отправки
>>>>>>> 2e5d7d31b57a90bcd1afa1b4b497613429e909bc
            submit_btn = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//input[@type='submit' or @value='Отправить']")))
            submit_btn.click()

<<<<<<< HEAD
=======
            # Ждем обработки отправки
>>>>>>> 2e5d7d31b57a90bcd1afa1b4b497613429e909bc
            time.sleep(2)
            return True
        except Exception as e:
            print(f"Ошибка отправки решения: {e}")
            return False

    def check_solution_status(self, max_attempts=10):
<<<<<<< HEAD
=======
        """Проверка статуса решения"""
>>>>>>> 2e5d7d31b57a90bcd1afa1b4b497613429e909bc
        for attempt in range(max_attempts):
            time.sleep(5)
            try:
                self.driver.get("https://acmp.ru/index.asp?main=status")
                time.sleep(2)

                status_table = self.driver.find_element(By.CLASS_NAME, "refresh")
                rows = status_table.find_elements(By.TAG_NAME, "tr")

                for i, row in enumerate(rows):
                    if i == 0:
                        continue

                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) >= 6:
                        author_cell = cells[2]
                        if "Захаров Илья Николаевич" in author_cell.text:
                            result_cell = cells[5]
                            result_text = result_cell.text.strip()

                            if "Accepted" in result_text:
                                return True, "Accepted"
                            elif "Compiling" in result_text or "Testing" in result_text:
                                continue
                            else:
                                return False, result_text
            except Exception as e:
                print(f"Ошибка проверки статуса: {e}")
                continue

        return False, "Timeout"

<<<<<<< HEAD
    def solve_task_with_retry(self, task_url, task_id, max_attempts=3):
=======
    def solve_task_with_retry(self, task_url, task_id, max_attempts=2):
        """Решение одной задачи с повторными попытками"""
>>>>>>> 2e5d7d31b57a90bcd1afa1b4b497613429e909bc
        for attempt in range(1, max_attempts + 1):
            print(f"Попытка {attempt} для задачи {task_id}")

            try:
                self.driver.get(task_url)
                time.sleep(2)

<<<<<<< HEAD
=======
                # Проверяем, что страница загрузилась корректно
>>>>>>> 2e5d7d31b57a90bcd1afa1b4b497613429e909bc
                if "error" in self.driver.current_url.lower() or "ошибка" in self.driver.page_source.lower():
                    print("Ошибка загрузки страницы, пробуем снова...")
                    continue

                task_info = self.parse_task_page()

<<<<<<< HEAD
                prompt = f"""Реши задачу на python. Ввод и вывод осуществляй с консоли.
=======
                prompt = f"""Реши задачу на Python. Ввод и вывод осуществляй с консоли.
>>>>>>> 2e5d7d31b57a90bcd1afa1b4b497613429e909bc

ЗАГОЛОВОК: {task_info['title']}

ПОЛНОЕ ОПИСАНИЕ:
{task_info['full_description']}

ТРЕБОВАНИЯ К РЕШЕНИЮ:
1. Читай данные из стандартного ввода (input())
2. Выводи результат в стандартный вывод (print())
3. Учти все ограничения из условий
4. Проверь решение на предоставленных примерах
5. Код должен быть простым и эффективным

Напиши код на Python, который точно соответствует требованиям задачи."""

<<<<<<< HEAD
                solution = self.ask_ai(prompt, task_id)
=======
                solution = self.ask_ai(prompt)
>>>>>>> 2e5d7d31b57a90bcd1afa1b4b497613429e909bc

                code_match = re.search(r'```python\s*(.*?)\s*```', solution, re.DOTALL)
                if code_match:
                    python_code = code_match.group(1).strip()
                else:
                    code_match = re.search(r'```\s*(.*?)\s*```', solution, re.DOTALL)
                    if code_match:
                        python_code = code_match.group(1).strip()
                    else:
                        python_code = solution.strip()

                success = self.submit_solution(python_code)

                if success:
                    is_accepted, result = self.check_solution_status()
<<<<<<< HEAD
                    
                    # Сохраняем попытку в историю
                    self.add_solution_to_history(task_id, python_code, attempt, 
                                               "Accepted" if is_accepted else "Failed", 
                                               result)
                    
=======
>>>>>>> 2e5d7d31b57a90bcd1afa1b4b497613429e909bc
                    if is_accepted:
                        print(f"Задача {task_id} решена успешно!")
                        return True
                    elif attempt < max_attempts:
                        print(f"Попытка {attempt} не удалась: {result}")
                        time.sleep(3)
                    else:
                        print(f"Все попытки для задачи {task_id} исчерпаны")
                        return False
                elif attempt < max_attempts:
                    print(f"Ошибка отправки, пробуем снова...")
                    time.sleep(3)
                else:
                    return False

            except Exception as e:
                print(f"Ошибка при решении задачи {task_id}: {e}")
                if attempt < max_attempts:
                    time.sleep(3)
                else:
                    return False

        return False

    def run_all_tasks(self):
<<<<<<< HEAD
        print("Запуск ACMP решателя...")
        print(f"Загружено решений из истории: {len(self.solutions_history)} задач")
        print(f"Загружено лучших решений: {len(self.best_solutions)} задач")
=======
        """Основной цикл работы - решение всех задач с 1 по 1000"""
        print("Запуск ACMP решателя...")
>>>>>>> 2e5d7d31b57a90bcd1afa1b4b497613429e909bc

        try:
            self.driver.get("https://acmp.ru/index.asp?main=tasks")
            print("Страница загружена, ожидаем авторизации...")

            if not self.wait_for_authorization():
                print("Не удалось дождаться авторизации.")
                return

            print("Авторизация успешна, начинаем решение задач...")
            task_urls = self.get_all_task_urls()
            successful_tasks = 0

            for i, task_url in enumerate(task_urls, 1):
                print(f"\nОбрабатываем задачу {i}/1000")

                if self.solve_task_with_retry(task_url, i):
                    successful_tasks += 1
<<<<<<< HEAD
=======

                # Возвращаемся к списку задач между задачами
>>>>>>> 2e5d7d31b57a90bcd1afa1b4b497613429e909bc
                if i < len(task_urls):
                    self.driver.get("https://acmp.ru/index.asp?main=tasks")
                    time.sleep(2)

            print(f"\nРабота завершена!")
            print(f"Всего задач: {len(task_urls)}")
            print(f"Успешно решено: {successful_tasks}")
            print(f"Процент успеха: {successful_tasks / len(task_urls) * 100:.1f}%" if len(
                task_urls) > 0 else "Процент успеха: 0%")
<<<<<<< HEAD
            print(f"История сохранена в: {self.solutions_file}")
            print(f"Лучшие решения сохранены в: {self.best_solutions_file}")
=======
>>>>>>> 2e5d7d31b57a90bcd1afa1b4b497613429e909bc

        except Exception as e:
            print(f"Критическая ошибка: {e}")

    def close(self):
<<<<<<< HEAD
=======
        """Закрытие браузера"""
>>>>>>> 2e5d7d31b57a90bcd1afa1b4b497613429e909bc
        self.driver.quit()


if __name__ == "__main__":
    api_key = input("Введите ваш OpenRouter API ключ (или Enter для демо): ").strip()
    solver = ACMPSolverBrowser(api_key if api_key else None)
    try:
        solver.run_all_tasks()
    except KeyboardInterrupt:
        print("\nПрограмма прервана пользователем")
    except Exception as e:
        print(f"Неожиданная ошибка: {e}")
    finally:
        solver.close()