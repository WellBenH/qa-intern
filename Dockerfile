FROM python:3.7.3-alpine

WORKDIR /app

COPY json_files/ /app
COPY schemas/ /app
COPY qa_unit_intern_task.py /app

RUN pip install jsonschema

ENV NAME World

ENTRYPOINT ["python"]

CMD ["qa_unit_intern_task.py"]