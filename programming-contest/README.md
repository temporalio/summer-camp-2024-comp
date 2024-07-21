# Solving Competitive Programming Problems with AI

Having to output the letters A-Z reminded me of CodeForces, a site where programmers can work on competitive programming problems. 
Contests generally have a certain number of problems in increasing difficulty, labeled A, B, C and so on.

This submission uses Temporal as well as ChatGPT to generate and test human or AI-generated solutions, and then output whether the given code passes test cases. 

## Installation and Setup

Navigate to the `programming-contest` file.

On one terminal:

```
temporal server start-dev
```

On another terminal:

``` 
go build
./programming-contest
```

## Additional Things to do

Putting your own Openai API Key allows the workflow to use ChatGPT-3.5 in order to generate AI solutions to problems.
If this is ignored, the workflow will randomly pick from the solutions provided in `./sample-solutions`.
Unfortunately, my own OpenAI API key was rate-limited, so I wasn't able to properly test this functionality. 

If you would like to add your own problems for the workflow to attempt, you must put the problem statement in `./problems` as `<problem_name>.txt`. 
Corresponding `<problem_name>.in` and `<problem_name>.out` files should be put into `./testcases`, as well as sample `<problem_name>.py` solutions in `./sample-solutions` if not using ChatGPT.

## Explanation

### **Activities**:
   - `DefaultSolutionActivity`: Returns one of the pre-written solutions to the problem, of which some will pass and others will fail
   - `ChatGPTSolutionActivity`: Returns a solution to the problem from ChatGPT
   - `TrySolutionActivity`: Tries to run the code with the test case input, then returns the output
   - `CheckOutputActivity`: Checks the actual output with the expected output, returns whether they match
### **Workflow**:
   - `SolveProblemWorkflow`: Solves a single problem, will return the elapsed time and the solution code if the solution is valid
   - `ProgrammingContestWorkflow`: Generates a programming contest with 26 problems, then prints the results