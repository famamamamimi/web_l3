import unittest
from app import app


class OneSimpleTest(unittest.TestCase):
    """Всего один простой тест"""

    def test_app_starts(self):
        """Тест: Приложение запускается и главная страница работает"""
        # Создаем тестовый клиент
        test_client = app.test_client()

        # Делаем запрос к главной странице
        response = test_client.get('/')

        # Проверяем что страница загрузилась (код 200 = OK)
        self.assertEqual(response.status_code, 200)

        # Простая проверка что это наше Flask приложение
        # (обычно Flask возвращает HTML, проверяем наличие тега)
        html_content = response.data.decode('utf-8').lower()
        self.assertTrue(len(html_content) > 100)  # Не пустая страница


# Можно запускать командой: python -m pytest test_app.py -v
# Или: python test_app.py
if __name__ == '__main__':
    unittest.main()