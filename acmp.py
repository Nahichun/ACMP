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

    def wait_for_authorization(self):
        """Ожидание завершения авторизации пользователем"""
        print("⏳ Ожидаем авторизации...")

        max_wait_time = 300  # 5 минут максимальное время ожидания
        start_time = time.time()

        while time.time() - start_time < max_wait_time:
            try:
                # Проверяем наличие элементов, указывающих на авторизацию
                user_elements = self.driver.find_elements(By.XPATH,
                                                          "//*[contains(text(), 'Выход') or contains(text(), 'Logout') or contains(text(), 'Захаров И.Н.')]")

                if user_elements:
                    print("✅ Авторизация обнаружена!")
                    return True

                # Также проверяем наличие кнопки входа
                login_elements = self.driver.find_elements(By.XPATH,
                                                           "//*[contains(text(), 'Вход') or contains(text(), 'Login')]")
                if login_elements:
                    print("⚠️  Необходима авторизация! Пожалуйста, войдите в систему.")

                print(f"⏰ Ожидание... ({int(time.time() - start_time)} сек.)")
                time.sleep(5)

            except Exception as e:
                print(f"Ошибка при проверке авторизации: {e}")
                time.sleep(5)

        print("❌ Превышено время ожидания авторизации")
        return False

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

        # Получаем описание из meta тега
        description = ""
        try:
            meta_desc = self.driver.find_element(By.XPATH, "//meta[@name='description']")
            description = meta_desc.get_attribute("content")
            print(f"Описание из meta: {description[:100]}...")
        except:
            print("Не удалось получить описание из meta")

        # Дополнительно получаем текст задачи со страницы
        full_text = ""
        try:
            content_div = self.driver.find_element(By.XPATH, "//td[contains(@background, 'notepad2.gif')]")
            paragraphs = content_div.find_elements(By.TAG_NAME, "p")
            for p in paragraphs:
                if p.text.strip():
                    full_text += p.text.strip() + "\n"
        except:
            pass

        # Объединяем оба источника
        complete_description = description + "\n" + full_text

        return {
            'title': title,
            'description': complete_description[:800] + "..." if len(
                complete_description) > 800 else complete_description,
            'full_description': complete_description
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

            # РЕАЛЬНАЯ ОТПРАВКА
            submit_btn = self.driver.find_element(By.XPATH, "//input[@type='submit' or @value='Отправить']")
            submit_btn.click()
            print("🚀 Решение отправлено!")
            time.sleep(3)

            return True

        except Exception as e:
            print(f"❌ Ошибка при подготовке отправки: {e}")
            return False

    def check_solution_status(self, max_attempts=15, wait_time=5):
        """Проверка статуса решения на странице статуса"""
        print("🔍 Проверяем результат решения...")

        for attempt in range(max_attempts):
            print(f"Попытка {attempt + 1}/{max_attempts}...")
            time.sleep(wait_time)

            # Обновляем страницу статуса
            self.driver.get("https://acmp.ru/index.asp?main=status")
            time.sleep(2)

            try:
                # Ищем таблицу с результатами
                status_table = self.driver.find_element(By.CLASS_NAME, "refresh")
                rows = status_table.find_elements(By.TAG_NAME, "tr")

                # Ищем строку с нашим пользователем
                for i, row in enumerate(rows):
                    if i == 0:  # Пропускаем заголовок
                        continue

                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) >= 6:
                        author_cell = cells[2]  # Столбец с автором

                        # Проверяем, содержит ли ячейка наше имя
                        if "Захаров Илья Николаевич" in author_cell.text:
                            result_cell = cells[5]  # Столбец с результатом
                            result_text = result_cell.text.strip()

                            print(f"Найдена наша попытка: {result_text}")

                            if "Accepted" in result_text:
                                print("🎉 Решение принято!")
                                return True, "Accepted"
                            elif "Compiling" in result_text or "Testing" in result_text:
                                print("⏳ Решение проверяется...")
                                continue  # Продолжаем ждать
                            else:
                                print(f"❌ Решение не принято: {result_text}")
                                return False, result_text

                print("Наша попытка еще не появилась в таблице...")

            except Exception as e:
                print(f"Ошибка при проверке статуса: {e}")
                continue

        print("⚠️ Превышено время ожидания результата")
        return False, "Timeout"

    def solve_task_with_retry(self, task_url, max_attempts=3):
        """Решение одной задачи с повторными попытками при неудаче"""
        print(f"\n🚀 Переходим к задаче: {task_url}")

        for attempt in range(1, max_attempts + 1):
            print(f"\n📝 Попытка {attempt}/{max_attempts}")

            # Переходим на страницу задачи
            self.driver.get(task_url)
            time.sleep(3)

            # Прокручиваем к форме решения
            try:
                solution_section = self.driver.find_element(By.XPATH, "//a[@name='solution']")
                self.driver.execute_script("arguments[0].scrollIntoView();", solution_section)
                time.sleep(1)
            except:
                print("⚠️  Не удалось найти раздел решения")

            # Парсим информацию о задаче
            task_info = self.parse_task_page()

            # Формируем промпт для нейросети с полным текстом задачи
            prompt = f"""Реши задачу на Python. Ввод и вывод осуществляй с консоли.

Задача: {task_info['title']}

Полное описание:
{task_info['full_description']}

Напиши код на Python, который читает входные данные из стандартного ввода и выводит результат в стандартный вывод.
Код должен быть простым и эффективным. Убедись, что решение корректно обрабатывает все граничные случаи."""

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
                print("✅ Решение отправлено! Проверяем результат...")
                # Проверяем статус решения
                is_accepted, result = self.check_solution_status()

                if is_accepted:
                    print("🎉 Задача решена успешно!")
                    return True
                else:
                    print(f"❌ Попытка {attempt} не удалась: {result}")

                    if attempt < max_attempts:
                        print("🔄 Пробуем решить задачу заново...")
                        # Небольшая пауза перед следующей попыткой
                        time.sleep(3)
                    else:
                        print(f"❌ Все {max_attempts} попытки исчерпаны для этой задачи")
                        return False
            else:
                print("❌ Ошибка отправки решения.")
                if attempt < max_attempts:
                    print("🔄 Пробуем еще раз...")
                    time.sleep(3)
                else:
                    return False

        return False

    def run(self):
        """Основной цикл работы"""
        print("🌐 Запускаем браузер...")
        print("📝 Открываем acmp.ru...")

        # Открываем главную страницу
        self.driver.get("https://acmp.ru/index.asp?main=tasks")
        time.sleep(3)

        # Ждем завершения авторизации
        if not self.wait_for_authorization():
            print("❌ Не удалось дождаться авторизации. Программа завершена.")
            return

        # Извлекаем ссылки на задачи
        print("\n🔍 Ищем задачи...")
        task_links = self.extract_task_links()

        print(f"\n📊 Найдено задач: {len(task_links)}")

        if not task_links:
            print("❌ Задачи не найдены. Проверьте структуру страницы.")
            return

        # Обрабатываем задачи
        max_tasks = 5  # Можно увеличить это число
        successful_tasks = 0
        attempted_tasks = 0

        for i, task_link in enumerate(task_links[:max_tasks], 1):
            print(f"\n{'=' * 60}")
            print(f"🎯 ЗАДАЧА {i}/{max_tasks} - {task_link}")
            print(f"{'=' * 60}")

            attempted_tasks += 1

            # Решаем задачу с повторными попытками
            if self.solve_task_with_retry(task_link):
                successful_tasks += 1
            else:
                print(f"⚠️ Пропускаем задачу после неудачных попыток")

            # Возвращаемся к списку задач (если это не последняя задача)
            if i < min(len(task_links), max_tasks):
                print("\n↩️  Возвращаемся к списку задач...")
                self.driver.get("https://acmp.ru/index.asp?main=tasks")
                time.sleep(3)

        print(f"\n{'=' * 60}")
        print(f"🎉 РАБОТА ЗАВЕРШЕНА!")
        print(f"📊 Статистика:")
        print(f"   Всего задач: {attempted_tasks}")
        print(f"   Успешно решено: {successful_tasks}")
        print(f"   Процент успеха: {successful_tasks / attempted_tasks * 100:.1f}%")
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
            for link in task_links[:10]:
                print(f"  - {link}")
            input("Нажмите Enter чтобы закрыть...")
        finally:
            solver.close()