.PHONY: all clean test
all: test

clean:
	@find .. -name '*~' -delete

test: ../cmpds.py ./gends.py
	@./test.sh
