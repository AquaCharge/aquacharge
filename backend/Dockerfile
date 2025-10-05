FROM python:3.11-slim

WORKDIR /aquacharge

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


COPY . .

ENV HOST=0.0.0.0
ENV FLASK_ENV=development
ENV FLASK_APP=app.py

EXPOSE 5050

CMD ["flask", "run", "--host=0.0.0.0", "--port=5050"]
