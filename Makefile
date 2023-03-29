# Why do you use Makefile?  Because it works..
install:
	pipenv install

test: 
	pipenv run python test_fim.py

container: 
	pipenv lock --requirements > requirements.txt
	podman build . -t fim:latest

run:
	pipenv run python fim.py
