package main

import (
	"fmt"
	"sync"
	"time"
)

type EMailJob struct {
	email string
}

func producers(emailChannel chan<- EMailJob, wg *sync.WaitGroup) {
	defer wg.Done()
	for i := 0; i < 5; i++ {
		emailTask := EMailJob{email: "something"}
		emailChannel <- emailTask
		fmt.Printf("produced job %s", emailTask.email)
		time.Sleep(time.Millisecond * 200)
	}
}

func consumers(emailChannel <-chan EMailJob, wg *sync.WaitGroup) {
	defer wg.Done()
	for task := range emailChannel {
		fmt.Printf("EMail task consumed %s", task.email)
		time.Sleep(time.Millisecond * 200)
	}
}

func main() {
	// create buffered channel
	emailChannel := make(chan EMailJob, 5)
	// variable to hold waitGroup
	var producerWg sync.WaitGroup
	var consumerWg sync.WaitGroup

	// no of producers
	numOfProducers := 3
	producerWg.Add(numOfProducers)
	for i := 0; i < numOfProducers; i++ {
		go producers(emailChannel, &producerWg)
	}

	// no of consumers
	numOfConsumers := 3
	consumerWg.Add(numOfConsumers)
	for i := 0; i < numOfConsumers; i++ {
		go consumers(emailChannel, &consumerWg)
	}

	// finally wait for all jobs to get over
	producerWg.Wait()
	close(emailChannel)

	consumerWg.Wait()
}
