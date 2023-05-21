FROM python:3.10-slim-buster

ENV MONGODB_CONNECTION ''
ENV TELEGRAM_TOKEN ''
ENV ADMIN_STRING 'admin_reg'

WORKDIR /python-docker

COPY requirenments.txt .
RUN pip3 install -r requirenments.txt

COPY python/*.py ./

CMD [ "python3", "-u", "main_menu.py"]