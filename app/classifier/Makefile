CC=$(CROSS_COMPILE)gcc

all: classifier

classifier: classifier.c
	$(CC) -O2 -Wall classifier.c -o classifier -lm

clean:
	rm -f classifier
