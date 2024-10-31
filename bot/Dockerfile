FROM python:3.12-slim

# Set the working directory
RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

COPY requirements.txt .

# Install dependencies
RUN pip install -U pip
RUN pip install --no-cache-dir --upgrade -r requirements.txt

COPY . .

CMD ["python", "bot.py"]
