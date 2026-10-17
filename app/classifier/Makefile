CC=$(CROSS_COMPILE)gcc

all: classifier

classifier: classifier.c
	$(CC) -O2 -Wall classifier.c -o classifier -lm

clean:
	rm -f classifier test/classifier-native

# Host build and tests (need python3 with numpy and scipy): see test/README.md
host-test: classifier.c
	gcc -O2 -Wall -Wextra -Wno-unused-parameter -o test/classifier-native classifier.c -lm

test: host-test
	cd test && python3 parity.py && python3 synth_test.py
