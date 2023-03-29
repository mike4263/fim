# Why do you use Makefile?  Because it works..
install:
	pipenv install

test: 
	pipenv run python test_fim.py


docker: 
	podman build . -t fim:latest
