from flask import Flask, render_template, request, send_file
from PIL import Image, ImageDraw
import numpy as np
import io
import base64
import os
import requests

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/images'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

RECAPTCHA_SITE_KEY = "6LdyaBYsAAAAACyUnXmvWZuWD3o2U0vZ1P8_nBw7"
RECAPTCHA_SECRET_KEY = "6LdyaBYsAAAAADfC83TrEor1NW3hu78hKtTREi3x"


def verify_recaptcha(response_token):
    data = {
        'secret': RECAPTCHA_SECRET_KEY,
        'response': response_token
    }

    try:
        response = requests.post(
            'https://www.google.com/recaptcha/api/siteverify',
            data=data,
            timeout=5
        )
        result = response.json()
        return result.get('success', False)
    except requests.RequestException:
        return False


def add_noise(image, noise_level):
    img_array = np.array(image)
    noise_factor = noise_level / 100.0
    noise = np.random.normal(0, noise_factor * 255, img_array.shape)
    noisy_array = img_array + noise
    noisy_array = np.clip(noisy_array, 0, 255).astype(np.uint8)
    return Image.fromarray(noisy_array)


def create_color_histogram(image, title):
    """Создает гистограмму цветов без matplotlib"""
    img_array = np.array(image)

    # Размеры гистограммы
    width, height = 800, 400
    hist_img = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(hist_img)

    # Цвета каналов
    colors = ['red', 'green', 'blue']
    channel_data = []

    # Собираем данные по каналам
    for i in range(3):
        channel = img_array[:, :, i].flatten()
        hist, bins = np.histogram(channel, bins=256, range=(0, 255))
        hist = hist / hist.max()  # Нормализуем
        channel_data.append(hist)

    # Рисуем оси
    draw.line([(50, 50), (50, height - 50)], fill='black', width=2)  # Y ось
    draw.line([(50, height - 50), (width - 50, height - 50)], fill='black', width=2)  # X ось

    # Подписи осей
    draw.text((30, 20), title, fill='black')
    draw.text((width // 2, height - 30), 'Значение пикселя', fill='black')
    draw.text((10, height // 2), 'Частота', fill='black', angle=90)

    # Рисуем гистограммы для каждого канала
    for i, color in enumerate(colors):
        hist = channel_data[i]
        color_map = {'red': (255, 0, 0), 'green': (0, 255, 0), 'blue': (0, 0, 255)}

        # Рисуем график
        for j in range(255):
            x1 = 50 + j * (width - 100) // 256
            x2 = 50 + (j + 1) * (width - 100) // 256

            y1 = height - 50 - int(hist[j] * (height - 100))
            y2 = height - 50 - int(hist[j + 1] * (height - 100))

            # Полупрозрачное закрашивание
            overlay = Image.new('RGBA', (x2 - x1, height - 50 - y1), (*color_map[color], 50))
            hist_img.paste(overlay, (x1, y1), overlay)

            # Линия графика
            draw.line([(x1, y1), (x2, y2)], fill=color_map[color], width=2)

    # Легенда
    legend_y = 70
    for i, color in enumerate(colors):
        color_map = {'red': (255, 0, 0), 'green': (0, 255, 0), 'blue': (0, 0, 255)}
        draw.rectangle([width - 150, legend_y + i * 30, width - 130, legend_y + i * 30 + 15],
                       fill=color_map[color])
        draw.text((width - 125, legend_y + i * 30), f'{color.upper()} канал', fill='black')

    # Сохраняем в буфер
    buf = io.BytesIO()
    hist_img.save(buf, format='PNG', quality=95)
    buf.seek(0)

    return buf


@app.route('/', methods=['GET', 'POST'])
def index():
    original_hist = None
    noisy_hist = None
    noisy_image_data = None
    message = ""
    captcha_error = ""

    if request.method == 'POST':
        recaptcha_response = request.form.get('g-recaptcha-response')
        if not recaptcha_response:
            captcha_error = "Пожалуйста, подтвердите, что вы не робот"
        elif not verify_recaptcha(recaptcha_response):
            captcha_error = "Ошибка проверки reCAPTCHA. Попробуйте еще раз."
        else:
            if 'image' not in request.files:
                message = "Файл не выбран"
            else:
                file = request.files['image']

                if file.filename == '':
                    message = "Файл не выбран"
                else:
                    try:
                        noise_level = int(request.form.get('noise_level', 20))
                        image = Image.open(file.stream)

                        original_hist_buf = create_color_histogram(image, "Исходное изображение")
                        original_hist = base64.b64encode(original_hist_buf.getvalue()).decode('utf-8')

                        noisy_image = add_noise(image, noise_level)

                        noisy_hist_buf = create_color_histogram(noisy_image, "Зашумленное изображение")
                        noisy_hist = base64.b64encode(noisy_hist_buf.getvalue()).decode('utf-8')

                        noisy_img_buf = io.BytesIO()
                        noisy_image.save(noisy_img_buf, format='PNG')
                        noisy_img_buf.seek(0)
                        noisy_image_data = base64.b64encode(noisy_img_buf.getvalue()).decode('utf-8')

                        message = f"Обработка завершена успешно! Уровень шума: {noise_level}%"

                    except Exception as e:
                        message = f"Ошибка при обработке изображения: {str(e)}"

    return render_template('index.html',
                           original_hist=original_hist,
                           noisy_hist=noisy_hist,
                           noisy_image=noisy_image_data,
                           message=message,
                           captcha_error=captcha_error,
                           recaptcha_site_key=RECAPTCHA_SITE_KEY)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)