package main

import (
	"context"
	"log"
	"log/slog"
	"os"

	"time"

	"go.temporal.io/api/enums/v1"
	"go.temporal.io/sdk/client"
	tlog "go.temporal.io/sdk/log"
	"go.temporal.io/sdk/worker"
	"go.temporal.io/sdk/workflow"
)

type Result struct {
	Name   string
	Claims int
}

func Game(ctx workflow.Context) error {
	logger := workflow.GetLogger(ctx)

	scavengers := []workflow.Future{
		workflow.ExecuteChildWorkflow(ctx, Scavenger, "Red", 'A', 'Z'),
		workflow.ExecuteChildWorkflow(ctx, Scavenger, "Blue", 'A', 'Z'),
		workflow.ExecuteChildWorkflow(ctx, Scavenger, "Green", 'A', 'Z'),
		workflow.ExecuteChildWorkflow(ctx, Scavenger, "Yellow", 'A', 'Z'),
	}

	for _, scavenger := range scavengers {
		var result Result
		err := scavenger.Get(ctx, &result)
		if err != nil {
			return err
		}
		logger.Info("Scavenger", "name", result.Name, "claims", result.Claims)
	}

	return nil
}

func Scavenger(ctx workflow.Context, name string, start rune, stop rune) (Result, error) {
	logger := workflow.GetLogger(ctx)

	ao := workflow.ActivityOptions{
		StartToCloseTimeout: 1 * time.Second,
	}
	ctx = workflow.WithActivityOptions(ctx, ao)

	claims := 0

	for c := start; c <= stop; c++ {
		ctx := workflow.WithChildOptions(ctx, workflow.ChildWorkflowOptions{
			WorkflowID:            "claim-" + string(c),
			WorkflowIDReusePolicy: enums.WORKFLOW_ID_REUSE_POLICY_REJECT_DUPLICATE,
		})
		err := workflow.ExecuteChildWorkflow(ctx, Claim, c, name).Get(ctx, nil)
		if err == nil {
			claims++
		} else {
			logger.Warn("Failed claim", "scavenger", name, "error", err)
		}
	}

	return Result{Name: name, Claims: claims}, nil
}

func Claim(ctx workflow.Context, letter rune, claimant string) error {
	logger := workflow.GetLogger(ctx)

	logger.Info("Claim!", "letter", letter, "scavenger", claimant)

	return nil
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

	w := worker.New(c, "scavenger", worker.Options{})

	w.RegisterWorkflow(Game)
	w.RegisterWorkflow(Scavenger)
	w.RegisterWorkflow(Claim)
	err = w.Start()
	if err != nil {
		log.Fatalln("Unable to start worker", err)
	}

	workflowOptions := client.StartWorkflowOptions{
		ID:        "scavenger",
		TaskQueue: "scavenger",
	}

	we, err := c.ExecuteWorkflow(context.Background(), workflowOptions, Game)
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
