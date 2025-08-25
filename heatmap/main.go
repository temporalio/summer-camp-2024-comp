package main

import (
	"context"
	"fmt"
	"io"
	"log"
	"log/slog"
	"strings"
	"time"

	"github.com/common-nighthawk/go-figure"
	"go.temporal.io/sdk/client"
	tlog "go.temporal.io/sdk/log"
	"go.temporal.io/sdk/temporal"
	"go.temporal.io/sdk/worker"
	"go.temporal.io/sdk/workflow"
)

var noopLogger = tlog.NewStructuredLogger(slog.New(slog.NewTextHandler(io.Discard, nil)))

const (
	taskQueue   = "heatmap"
	letters     = "abcdefghijklmnopqrstuvwxyz"
	fontName    = "letters"
	pointWidth  = time.Second
	pointHeight = 3
)

func Heatmap(ctx workflow.Context) error {
	ctx = workflow.WithActivityOptions(ctx, workflow.ActivityOptions{
		StartToCloseTimeout: time.Millisecond * 2000,
		RetryPolicy: &temporal.RetryPolicy{
			MaximumAttempts: 1,
		},
	})
	f := figure.NewFigure(strings.ToUpper(letters), fontName, true)
	// Add an empty row at the top and bottom to make the heatmap look better
	rows := []string{""}
	rows = append(rows, f.Slicify()...)
	rows = append(rows, "")

	maxRowLen := len(rows[0])
	for _, row := range rows {
		if len(row) > maxRowLen {
			maxRowLen = len(row)
		}
	}
	maxRowLen++

	// Each column is rendered by a single workflow task that schedules a bunch of activities and timers
	for c := 0; c < maxRowLen; c++ {
		var futures []workflow.Future
		for r, row := range rows {
			if c >= len(row) || row[c] == ' ' {
				// To print an empty "pixel" we execute `pointHeight` simultaneous timers that will be rendered in a column
				for i := 0; i < pointHeight; i++ {
					futures = append(futures, workflow.NewTimer(ctx, pointWidth))
				}
			} else {
				// To print an colored "pixel" we execute `pointHeight` activities.
				// It's important that their ids differ so that the timeline will not collapse them and
				// show them separately on top of each other.
				for i := 0; i < pointHeight; i++ {
					futures = append(futures, workflow.ExecuteActivity(ctx, fmt.Sprintf("%d-%d", r, i)))
				}
			}
		}
		for _, f := range futures {
			_ = f.Get(ctx, nil)
		}
	}
	return nil
}

func main() {
	c, err := client.Dial(client.Options{
		HostPort: client.DefaultHostPort,
		Logger:   noopLogger,
	})
	if err != nil {
		log.Fatalln("Unable to create client", err)
	}
	defer c.Close()

	w := worker.New(c, taskQueue, worker.Options{
		MaxConcurrentWorkflowTaskPollers: 50,
		MaxConcurrentActivityTaskPollers: 100,
	})
	w.RegisterWorkflow(Heatmap)

	if err = w.Start(); err != nil {
		log.Fatalln("Unable to start worker", err)
	}

	ctx := context.Background()
	we, err := c.ExecuteWorkflow(ctx, client.StartWorkflowOptions{
		ID:        "heatmap",
		TaskQueue: taskQueue,
	}, Heatmap)
	if err != nil {
		log.Fatalln("Unable to execute workflow", err)
	}
	log.Printf("Take a look at compact event history of http://localhost:8233/namespaces/default/workflows/%s/%s/history with labs enabled and 10%% zoom\n", we.GetID(), we.GetRunID())

	if err = we.Get(ctx, nil); err != nil {
		log.Fatalln("Unable get workflow result", err)
	}

	w.Stop()
}
