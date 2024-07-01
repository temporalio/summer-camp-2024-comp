package main

import (
	"context"
	"log"
	"log/slog"
	"os"

	"time"

	"go.temporal.io/sdk/client"
	tlog "go.temporal.io/sdk/log"
	"go.temporal.io/sdk/worker"
	"go.temporal.io/sdk/workflow"
)

var a *Activities

func Umpire(ctx workflow.Context) error {
	var winners = map[string]int{
		"Red":  0,
		"Blue": 0,
	}

	for c := 'A'; c <= 'Z'; c++ {
		red := workflow.ExecuteChildWorkflow(ctx, Racer, 'A', c)
		blue := workflow.ExecuteChildWorkflow(ctx, Racer, 'A', c)

		var err error
		var winner string

		selector := workflow.NewSelector(ctx)
		selector.AddFuture(red, func(f workflow.Future) {
			if err = f.Get(ctx, nil); err != nil {
				log.Printf("Red error: %v", err)
				winner = "Blue"
			} else {
				winner = "Red"
			}
		})
		selector.AddFuture(blue, func(f workflow.Future) {
			if err = f.Get(ctx, nil); err != nil {
				log.Printf("Blue error: %v", err)
				winner = "Red"
			} else {
				winner = "Blue"
			}
		})
		selector.Select(ctx)
		winners[winner]++

		log.Printf("Race: %c Winner: %s", c, winner)
	}

	log.Printf("Results: Red: %d Blue: %d", winners["Red"], winners["Blue"])

	return nil
}

func Racer(ctx workflow.Context, start rune, stop rune) error {
	ao := workflow.ActivityOptions{
		StartToCloseTimeout: 1 * time.Second,
	}
	ctx = workflow.WithActivityOptions(ctx, ao)

	for c := start; c <= stop; c++ {
		err := workflow.ExecuteActivity(ctx, a.Tag, string(c)).Get(ctx, nil)
		if err != nil {
			return err
		}
	}

	return nil
}

type Activities struct{}

func (a *Activities) Tag() (letter string, err error) {
	return letter, nil
}

func main() {
	c, err := client.Dial(client.Options{
		HostPort: client.DefaultHostPort,
		Logger: tlog.NewStructuredLogger(
			slog.New(slog.NewTextHandler(os.Stdout, &slog.HandlerOptions{
				Level: slog.LevelInfo,
			})),
		),
	})
	if err != nil {
		log.Fatalln("Unable to create client", err)
	}
	defer c.Close()

	w := worker.New(c, "race", worker.Options{})

	w.RegisterWorkflow(Umpire)
	w.RegisterWorkflow(Racer)
	activities := &Activities{}
	w.RegisterActivity(activities)
	err = w.Start()
	if err != nil {
		log.Fatalln("Unable to start worker", err)
	}

	workflowOptions := client.StartWorkflowOptions{
		ID:        "race",
		TaskQueue: "race",
	}

	we, err := c.ExecuteWorkflow(context.Background(), workflowOptions, Umpire)
	if err != nil {
		log.Fatalln("Unable to execute workflow", err)
	}
	log.Println("Started workflow", "WorkflowID", we.GetID(), "RunID", we.GetRunID())

	var result string
	err = we.Get(context.Background(), &result)
	if err != nil {
		log.Fatalln("Unable get workflow result", err)
	}
	log.Println("Workflow result:", result)

	w.Stop()
}
