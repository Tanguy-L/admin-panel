FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .


ENV PLG_HOST=0.0.0.0
ENV PLG_PORT=3306
ENV PLG_USERNAME=plg
ENV PLG_DATABASE=plg
ENV PLG_PASSWORD=*
ENV APP_HOST=0.0.0.0
ENV APP_PORT=5000
ENV APP_USERNAME=plg
ENV APP_PASSWORD=*

ENV FLASK_APP=app.py
ENV FLASK_ENV=production
# CMD ["gunicorn", "app:application", "--bind 0.0.0.0:5000"]
CMD ["python", "-m", "flask", "run", "--host=0.0.0.0"]
