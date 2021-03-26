FROM python:3.8

WORKDIR /app
COPY requirements.txt .
RUN  pip3 install -r requirements.txt

COPY main.py .
RUN chmod +x main.py
EXPOSE 8080
CMD python3 main.py
