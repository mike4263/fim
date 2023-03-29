FROM fedora:37
COPY . /app

ENV HOME /app

RUN dnf install -y python3 pip which
RUN cd /app && pip install -r requirements.txt \
    && mkdir -p /var/fim/ \
    && mkdir -p /app/.local \
    && chmod 777 /app/.local 

WORKDIR /app
ENTRYPOINT ["python3", "fim.py"] 
