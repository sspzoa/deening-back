FROM python:3.12.7-alpine

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./app /code/app

ARG OPENAI_API_KEY
ARG ACCESS_TOKEN
ARG MONGODB_URL

ENV OPENAI_API_KEY=${OPENAI_API_KEY}
ENV ACCESS_TOKEN=${ACCESS_TOKEN}
ENV MONGODB_URL=${MONGODB_URL}

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]