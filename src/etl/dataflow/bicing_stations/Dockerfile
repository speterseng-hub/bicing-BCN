FROM apache/beam_python3.12_sdk:2.62.0

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py /template/main.py

ENTRYPOINT ["python", "/template/main.py"]
