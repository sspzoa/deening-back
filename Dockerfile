FROM python:3.12.5-alpine

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./app /code/app

ARG OPENAI_API_KEY
ARG ACCESS_TOKEN

ENV OPENAI_API_KEY=${OPENAI_API_KEY}
ENV ACCESS_TOKEN=${ACCESS_TOKEN}

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]