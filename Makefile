# Why do you use Makefile?  Because it works..
install:
	pipenv install

test: install
	pipenv run python test_fim.py
