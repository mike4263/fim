# Why do you use Makefile?  Because it works..
install:
	pipenv install

test: 
	pipenv run python test_fim.py


docker: test
	docker build . -t fim:latest
