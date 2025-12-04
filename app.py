from flask import Flask, render_template, request, send_file
from PIL import Image
import matplotlib.pyplot as plt
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
    img_array = np.array(image)
    plt.figure(figsize=(10, 6))
    colors = ['red', 'green', 'blue']

    for i, color in enumerate(colors):
        plt.hist(img_array[:, :, i].ravel(), bins=256, color=color, alpha=0.5,
                 label=f'{color.upper()} канал', density=True)

    plt.title(f'Распределение цветов - {title}')
    plt.xlabel('Значение пикселя')
    plt.ylabel('Плотность')
    plt.legend()
    plt.grid(True, alpha=0.3)

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    plt.close()

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

# ... существующий код ...

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)