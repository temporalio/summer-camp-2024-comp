temporal-local:
	temporal server start-dev

player-activities-worker:
	python -m src.workers.activity_worker -n player

game-workflow-worker:
	python -m src.workers.workflow_worker -n game

player-workflow-worker:
	python -m src.workers.workflow_worker -n player

start-game:
	python -m src.start_game
