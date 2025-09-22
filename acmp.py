from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
import time
import re
import requests
import json
import uuid
from urllib.parse import urljoin
import warnings

# Отключаем предупреждения SSL
warnings.filterwarnings("ignore", category=requests.packages.urllib3.exceptions.InsecureRequestWarning)


class ACMPSolverBrowser:
    def __init__(self, gigachat_auth_key=None):
        self.gigachat_auth_key = gigachat_auth_key
        self.access_token = None
        self.token_expiry = 0

        # Настройка браузера
        chrome_options = Options()
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-infobars")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("--ignore-certificate-errors")
        chrome_options.add_argument("--ignore-ssl-errors")

        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 15)

    def get_gigachat_token(self):
        """Получение токена доступа для GigaChat"""
        if self.access_token and time.time() < self.token_expiry:
            return self.access_token

        url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
        payload = {'scope': 'GIGACHAT_API_PERS'}
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json',
            'RqUID': str(uuid.uuid4()),
            'Authorization': f'Basic {self.gigachat_auth_key}'
        }

        try:
            # Отключаем проверку SSL для requests
            response = requests.post(url, headers=headers, data=payload, verify=False)
            response.raise_for_status()
            token_data = response.json()
            self.access_token = token_data['access_token']
            self.token_expiry = time.time() + 1800
            return self.access_token
        except Exception as e:
            print(f"Ошибка получения токена GigaChat: {e}")
            return None

    def ask_gigachat(self, prompt):
        """Запрос к нейросети GigaChat"""
        if not self.gigachat_auth_key:
            # Демо-режим: возвращаем простые решения для популярных задач
            demo_solutions = {
                "a+b": "a, b = map(int, input().split())\nprint(a + b)",
                "неглухой телефон": "n = int(input())\nprint(n)",
                "бисер": "n = int(input())\nprint(n + 1)",
                "арбузы": "n = int(input())\nweights = list(map(int, input().split()))\nprint(min(weights), max(weights))",
                "два бандита": "a, b = map(int, input().split())\nprint(b-1, a-1)"
            }

            for key, solution in demo_solutions.items():
                if key in prompt.lower():
                    return f"```python\n{solution}\n```"

            return "```python\n# Демо-режим: введите API ключ для реальных решений\nn = int(input())\nprint(n)\n```"

        token = self.get_gigachat_token()
        if not token:
            return "Ошибка: не удалось получить токен доступа"

        url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"

        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f'Bearer {token}'
        }

        payload = {
            "model": "GigaChat",
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7,
            "max_tokens": 2000
        }

        try:
            response = requests.post(url, headers=headers, json=payload, verify=False)
            response.raise_for_status()
            result = response.json()
            return result['choices'][0]['message']['content']
        except Exception as e:
            print(f"Ошибка запроса к GigaChat: {e}")
            return f"Ошибка: {str(e)}"

    def extract_task_links(self):
        """Извлечение ссылок на задачи через браузер"""
        print("Ищем задачи на странице...")

        # Ждем загрузки таблицы с задачами
        try:
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
            time.sleep(2)
        except:
            print("Таблица не найдена")
            return []

        # Ищем все ссылки на задачи
        task_links = []
        try:
            links = self.driver.find_elements(By.XPATH, "//a[contains(@href, 'main=task')]")

            for link in links:
                href = link.get_attribute("href")
                if href and 'id_task=' in href and href not in task_links:
                    task_links.append(href)
                    print(f"Найдена задача: {link.text} -> {href}")

        except Exception as e:
            print(f"Ошибка поиска ссылок: {e}")

        return task_links

    def parse_task_page(self):
        """Парсинг страницы задачи через браузер"""
        print("Анализируем задачу...")

        # Получаем заголовок
        try:
            title = self.driver.find_element(By.TAG_NAME, "h1").text
            print(f"Задача: {title}")
        except:
            title = "Неизвестная задача"

        # Получаем описание
        description = ""
        try:
            content_div = self.driver.find_element(By.XPATH, "//td[contains(@background, 'notepad2.gif')]")
            paragraphs = content_div.find_elements(By.TAG_NAME, "p")
            for p in paragraphs:
                if p.text.strip():
                    description += p.text.strip() + "\n"
        except:
            pass

        return {
            'title': title,
            'description': description[:500] + "..." if len(description) > 500 else description,
        }

    def set_code_in_codemirror(self, code):
        """Ввод кода в CodeMirror редактор"""
        try:
            # Попробуем несколько способов ввода кода в CodeMirror

            # Способ 1: через JavaScript
            js_script = f"""
            var editor = document.querySelector('.CodeMirror').CodeMirror;
            editor.setValue(`{code}`);
            """
            self.driver.execute_script(js_script)
            time.sleep(1)

            # Способ 2: через textarea (если доступно)
            try:
                textarea = self.driver.find_element(By.ID, "source")
                if textarea.is_displayed():
                    textarea.clear()
                    textarea.send_keys(code)
            except:
                pass

            print("✓ Код введен в редактор")
            return True

        except Exception as e:
            print(f"❌ Ошибка ввода кода: {e}")
            return False

    def select_language(self, lang="PY"):
        """Выбор языка программирования"""
        try:
            lang_select = self.driver.find_element(By.NAME, "lang")

            # JavaScript для установки значения
            js_script = f"""
            var select = arguments[0];
            select.value = '{lang}';
            var event = new Event('change', {{ bubbles: true }});
            select.dispatchEvent(event);
            """
            self.driver.execute_script(js_script, lang_select)

            print(f"✓ Выбран язык: Python")
            return True

        except Exception as e:
            print(f"❌ Ошибка выбора языка: {e}")
            return False

    def submit_solution(self, solution_code):
        """Отправка решения через браузер"""
        print("Подготавливаем отправку решения...")

        try:
            # Прокручиваем к форме
            form = self.driver.find_element(By.TAG_NAME, "form")
            self.driver.execute_script("arguments[0].scrollIntoView();", form)
            time.sleep(1)

            # Вводим код в редактор
            if not self.set_code_in_codemirror(solution_code):
                return False

            # Выбираем язык
            if not self.select_language("PY"):
                return False

            # Визуальная индикация
            try:
                code_editor = self.driver.find_element(By.CLASS_NAME, "CodeMirror")
                self.driver.execute_script("arguments[0].style.border = '3px solid #4CAF50';", code_editor)
            except:
                pass

            print("✅ Решение готово к отправке!")
            print("⚠️  Для реальной отправки раскомментируйте код в методе submit_solution()")

            # Демонстрационная пауза
            time.sleep(3)

            # ЗАКОММЕНТИРОВАНО ДЛЯ БЕЗОПАСНОСТИ - раскомментируйте для реальной отправки:
            # submit_btn = self.driver.find_element(By.XPATH, "//input[@type='submit' or @value='Отправить']")
            # submit_btn.click()
            # print("🚀 Решение отправлено!")
            # time.sleep(3)

            return True

        except Exception as e:
            print(f"❌ Ошибка при подготовке отправки: {e}")
            return False

    def solve_task(self, task_url):
        """Решение одной задачи"""
        print(f"\n🚀 Переходим к задаче: {task_url}")

        # Переходим на страницу задачи
        self.driver.get(task_url)
        time.sleep(3)  # Ждем загрузки

        # Прокручиваем к форме решения
        try:
            solution_section = self.driver.find_element(By.XPATH, "//a[@name='solution']")
            self.driver.execute_script("arguments[0].scrollIntoView();", solution_section)
            time.sleep(1)
        except:
            print("⚠️  Не удалось найти раздел решения")

        # Парсим информацию о задаче
        task_info = self.parse_task_page()

        # Формируем промпт для нейросети
        prompt = f"""Реши задачу на Python. Ввод и вывод осуществляй с консоли.

Задача: {task_info['title']}

Описание:
{task_info['description']}

Напиши код на Python, который читает входные данные из стандартного ввода и выводит результат в стандартный вывод.
Код должен быть простым и эффективным."""

        print("🤖 Запрашиваем решение у нейросети...")
        solution = self.ask_gigachat(prompt)

        # Извлекаем код
        code_match = re.search(r'```python\s*(.*?)\s*```', solution, re.DOTALL)
        if code_match:
            python_code = code_match.group(1).strip()
        else:
            python_code = solution.strip()

        print("💡 Получено решение:")
        print("=" * 50)
        print(python_code)
        print("=" * 50)

        # Отправляем решение
        success = self.submit_solution(python_code)

        if success:
            print("✅ Решение подготовлено!")
        else:
            print("❌ Ошибка подготовки решения.")

        return success

    def run(self):
        """Основной цикл работы"""
        print("🌐 Запускаем браузер...")
        print("📝 Открываем acmp.ru...")

        # Открываем главную страницу
        self.driver.get("https://acmp.ru/index.asp?main=tasks")
        time.sleep(3)

        # Проверяем авторизацию
        try:
            user_elements = self.driver.find_elements(By.XPATH,
                                                      "//*[contains(text(), 'Выход') or contains(text(), 'Logout')]")
            if user_elements:
                print("✅ Авторизация обнаружена")
            else:
                print("⚠️  Необходима авторизация!")
                print("Пожалуйста, авторизуйтесь в браузере и нажмите Enter чтобы продолжить...")
                input()
        except:
            print("⚠️  Не удалось проверить авторизацию")

        # Извлекаем ссылки на задачи
        print("\n🔍 Ищем задачи...")
        task_links = self.extract_task_links()

        print(f"\n📊 Найдено задач: {len(task_links)}")

        if not task_links:
            print("❌ Задачи не найдены. Проверьте структуру страницы.")
            return

        # Обрабатываем первые 2 задачи для демонстрации
        for i, task_link in enumerate(task_links[:2], 1):
            print(f"\n{'=' * 60}")
            print(f"🎯 ЗАДАЧА {i}/2 - {task_link}")
            print(f"{'=' * 60}")

            self.solve_task(task_link)

            # Возвращаемся к списку задач
            if i < len(task_links[:2]):
                print("\n↩️  Возвращаемся к списку задач...")
                self.driver.get("https://acmp.ru/index.asp?main=tasks")
                time.sleep(3)

        print(f"\n{'=' * 60}")
        print("🎉 ДЕМОНСТРАЦИЯ ЗАВЕРШЕНА!")
        print("📋 Просмотрите результаты в браузере")
        print("⏸️  Браузер останется открытым для просмотра")
        input("Нажмите Enter чтобы закрыть...")

    def close(self):
        """Закрытие браузера"""
        self.driver.quit()


# Упрощенная демонстрация работы с CodeMirror
def demonstrate_codemirror():
    """Демонстрация работы с редактором кода"""
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    driver = webdriver.Chrome(options=chrome_options)

    try:
        print("🎬 Демонстрация работы с редактором CodeMirror")
        driver.get("https://acmp.ru/index.asp?main=task&id_task=1")
        time.sleep(3)

        # Прокручиваем к редактору
        editor = driver.find_element(By.CLASS_NAME, "CodeMirror")
        driver.execute_script("arguments[0].scrollIntoView();", editor)
        time.sleep(1)

        # Вводим код через JavaScript
        test_code = "# Демонстрационный код\nn = int(input())\nprint(n * 2)"
        js_script = f"""
        var editor = document.querySelector('.CodeMirror').CodeMirror;
        editor.setValue(`{test_code}`);
        """
        driver.execute_script(js_script)

        print("✅ Код введен в редактор")
        print("👀 Посмотрите результат в браузере")
        input("Нажмите Enter чтобы закрыть...")

    finally:
        driver.quit()


if __name__ == "__main__":
    print("🤖 ACMP.RU AUTOSOLVER WITH BROWSER")
    print("1. Полный режим с браузером")
    print("2. Демонстрация редактора кода")
    print("3. Только парсинг задач")

    choice = input("Выберите режим (1-3): ").strip()

    if choice == "1":
        api_key = input("Введите ваш GigaChat API ключ (или Enter для демо): ").strip()
        solver = ACMPSolverBrowser(api_key if api_key else None)
        try:
            solver.run()
        finally:
            solver.close()

    elif choice == "2":
        demonstrate_codemirror()

    elif choice == "3":
        solver = ACMPSolverBrowser()
        try:
            solver.driver.get("https://acmp.ru/index.asp?main=tasks")
            task_links = solver.extract_task_links()
            print(f"Найдено {len(task_links)} задач:")
            for link in task_links[:5]:
                print(f"  - {link}")
            input("Нажмите Enter чтобы закрыть...")
        finally:
            solver.close()