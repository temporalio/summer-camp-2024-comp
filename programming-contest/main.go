package main

import (
	"bytes"
	"context"
	"fmt"
	"log"
	"log/slog"
	"math/rand"
	"os"
	"os/exec"
	"strings"
	"time"

	openai "github.com/sashabaranov/go-openai"
	"go.temporal.io/sdk/client"
	tlog "go.temporal.io/sdk/log"
	"go.temporal.io/sdk/worker"
	"go.temporal.io/sdk/workflow"
)

var a *Activities

// Activities

type Activities struct{}

// Alternative to GetCodeFromChatGPTActivity if you have no tokens
func (a *Activities) ReturnRandomResultActivity(ctx context.Context, problemName string) (string, error) {	
	// Pick a random solution that might pass or fail
    randNum := rand.Intn(2)
	stringName := ""
	if(randNum == 0){
		stringName = "sample-solutions/"+problemName+"-pass" + ".py"
	}else{
		stringName = "sample-solutions/"+problemName+"-fail" + ".py"
	}

	content, err := os.ReadFile(stringName)
    if err != nil {
        return "", err
    }

    return string(content), nil
}

// Requests a solution from ChatGPT
func (a *Activities) GetCodeFromChatGPTActivity(ctx context.Context, apiKey string, problemName string) (string, error) {
	client := openai.NewClient(apiKey)
	content, err := os.ReadFile("problems/"+problemName + ".txt")
	if err != nil {
		return "",err
	}

	prompt := fmt.Sprintf("Write a Python program to solve this problem:\n\n%s.", string(content))
	resp, err := client.CreateChatCompletion(ctx, openai.ChatCompletionRequest{
		Model: "gpt-3.5-turbo",
		Messages: []openai.ChatCompletionMessage{
			{
				Role:    "user",
				Content: prompt,
			},
		},
	})
	if err != nil {
		return "", err
	}

	return resp.Choices[0].Message.Content, nil
}

// Trys to run the solution on the test case
func (a *Activities) TrySolutionActivity(ctx context.Context, code string, problemName string) (string, error) {
	// Read from input file
	input, err := os.ReadFile("testcases/" + problemName + ".in")
	if err != nil {
		return "", fmt.Errorf("failed to read input file: %w", err)
	}

    // Create a temp file to store code
    tmpFile, err := os.CreateTemp("testcases/", problemName + ".py")
    if err != nil {
        return "", fmt.Errorf("failed to create file: %w", err)
    }
    defer os.Remove(tmpFile.Name()) 


	if _, err := tmpFile.Write([]byte(code)); err != nil {
        return "", fmt.Errorf("failed to write to file: %w", err)
    }
    tmpFile.Close()

    // Create a command to run the Go code
    cmd := exec.Command("python3", tmpFile.Name())

    // input
    cmd.Stdin = bytes.NewBufferString(string(input))

    // output
    var out bytes.Buffer
    cmd.Stdout = &out
    cmd.Stderr = &out

    if err := cmd.Run(); err != nil {
		return "Failed to run Python program", nil
    }

    return out.String(), nil
}


func (a *Activities) CheckOutputActivity(ctx context.Context, output string, problemName string) (bool, error) {
	expectedOutput, err := os.ReadFile("testcases/" + problemName + ".out")
	if err != nil {
		return false, err
	}

	return string(expectedOutput) == string(output), nil
}

func ProgrammingContest(ctx workflow.Context, problemNames []string, api string) (string, error) {
	solvedCount := 0
	solutionMap := make(map[string]string)


	for i := 0; i < 26; i++ {
		// Solves each problem in problemNames, if less than 26, problems may be solved multiple times
		problemName := problemNames[i%len(problemNames)]
		we := workflow.ExecuteChildWorkflow(ctx, SolveProblem, api, problemName)

		var result SolveProblemResult

		// Retrieve the return values
		err := we.Get(ctx, &result)
		if err != nil {
			log.Printf("Error: %v", err)
		}

		if(result == SolveProblemResult{}){
			log.Printf("Problem: %c Name: %s Left Unsolved", rune('A' + i), problemName)
		}else{
			log.Printf("Problem: %c Name: %s Solved in: %.2f seconds", rune('A' + i), problemName, result.Elapsed.Seconds())
			solutionMap[problemName] = result.Code
			solvedCount++
		}
	}

	log.Printf("%d problems solved", solvedCount)

    var sb strings.Builder
    for key, value := range solutionMap {
        sb.WriteString(fmt.Sprintf("\n%s solution:\n\n%s\n\n", key, value))
    }

	return sb.String(), nil
}

type SolveProblemResult struct {
	Code     string
	Elapsed  time.Duration
}

func SolveProblem(ctx workflow.Context, APIKey, problemName string) (SolveProblemResult, error) {
	logger := workflow.GetLogger(ctx)

	ao := workflow.ActivityOptions{
		StartToCloseTimeout: time.Hour,
	}
	ctx = workflow.WithActivityOptions(ctx, ao)
	startTime := workflow.Now(ctx)

	var code string

	// Uncomment this activity to use ChatGPT

    // err := workflow.ExecuteActivity(ctx, a.GetCodeFromChatGPTActivity, APIKey, problemName).Get(ctx, &code)
    // if err != nil {
    //     logger.Error("GetCodeFromChatGPTActivity failed", "Error", err)
    //     return SolveProblemResult{}, err
    // }

	// Comment this activity when using ChatGPT
    err := workflow.ExecuteActivity(ctx, a.ReturnRandomResultActivity, problemName).Get(ctx, &code)
    if err != nil {
        logger.Error("ReturnResultActivity failed", "Error", err)
        return SolveProblemResult{}, err
    }

	var output string
    err = workflow.ExecuteActivity(ctx, a.TrySolutionActivity, code, problemName).Get(ctx, &output)
    if err != nil {
        logger.Error("TrySolutionActivity failed", "Error", err)
        return SolveProblemResult{}, err
    }

	var success bool
    err = workflow.ExecuteActivity(ctx, a.CheckOutputActivity, output, problemName).Get(ctx, &success)
    if err != nil {
        logger.Error("CheckOutputActivity failed", "Error", err)
        return SolveProblemResult{}, err
    }

	if(success){
		endTime := workflow.Now(ctx)
		elapsedTime := endTime.Sub(startTime)
		return SolveProblemResult{Code: code, Elapsed: elapsedTime}, nil
	}else{
		return SolveProblemResult{}, nil
	}
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
	
	// PUT OPENAI API TOKEN HERE
	api := "<OpenAI ChatGPT Token>"

	w := worker.New(c, "SolveProblem", worker.Options{})
	w.RegisterWorkflow(ProgrammingContest)
	w.RegisterWorkflow(SolveProblem)
	activities := &Activities{}
	w.RegisterActivity(activities)
	err = w.Start()
	if err != nil {
		log.Fatalln("Unable to start worker", err)
	}

	workflowOptions := client.StartWorkflowOptions{
		ID:        "SolveProblem",
		TaskQueue: "SolveProblem",
	}

	problemNames := []string{"sampleproblem1", "sampleproblem2"}

	we, err := c.ExecuteWorkflow(context.Background(), workflowOptions, ProgrammingContest, problemNames, api)
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