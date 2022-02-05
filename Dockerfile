FROM fedora:35
COPY . /app

ENV HOME /app

RUN dnf install -y python3 pipenv which
RUN cd /app && pipenv install --deploy --ignore-pipfile \
    && mkdir -p /var/fim/ \
    && mkdir /app/.local \
    && chmod 777 /app/.local 

WORKDIR /app
ENTRYPOINT ["pipenv", "run", "python", "fim.py"] 
