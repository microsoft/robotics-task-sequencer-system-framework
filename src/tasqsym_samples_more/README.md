## About

This directory contains examples for learning and testing more complicated behavior trees using the framework.

Note, the example codes under this directory is meant for understanding complicated behavior tree generation and execution. The directory is NOT meant for understanding the entire framework (please refer to tasqsym_samples to get a full understanding of the framework including examples of the hardware connection layer).

The below codes will not run an actual skill. Instead, the code will "print" colons followed by the details of the skill that is currently being executed by the system.

## Usage

### 1. Run the fallback sample

```
python ../robotics-task-sequencer-system-framework/src/tasqsym/core.py --config ./src/tasqsym_samples_more/core_settings.json --btfile ./src/tasqsym_samples_more/sample_sequence/fallback_example.json --connection standalone
```

You may also edit the fallback_example.json and switch the "@set_value" of the first node between "true" and "false" to see the difference in behavior.

### 2. Run the retry until sample

```
python ../robotics-task-sequencer-system-framework/src/tasqsym/core.py --config ./src/tasqsym_samples_more/core_settings.json --btfile ./src/tasqsym_samples_more/sample_sequence/retryuntil_example.json --connection standalone
```

You may also edit the retryuntil_example.json and switch the "@set_value" of the first node between "true" and "false" to see the difference in behavior ("false" will never terminate as will keep retrying).

### 3. Run the complex behavior tree generation sample

This example will require access to an Azure OpenAI resource.

```
python ../robotics-task-sequencer-system-framework/src/tasqsym_encoder/server.py --config ./src/tasqsym_samples_more/server_settings.json --aoai --aioutput --aimodel tasqsym_samples_more.aimodels.model.ComplexScenario --connection file --credentials <CREDENTIALS_FILE>
```

In the web browser UI, try entering ONE of the following sentences:
```
Pick up the cup on the table.
Throw away the cup on the table.
Wipe the table using a cloth until the table is clean.
Open the oven and get the cookies, then place the tray on the table.
Remove all cups from the table. If there’s anything left in the cup, pour it into the sink before throwing it away.
```

It is important to note that the system may not always return the correct behavior tree the first time. In such cases, a user should interactively correct the tree (e.g., if the ordering of the actions are incorrect, the ordering can be modified by further instructing "PickUp should be done before VisualCheck" etc.).

### 4. Run the generated complex behavior tree

This example requires running the previous example first to generate the tasqsym_encoder_output.json.

```
python ../robotics-task-sequencer-system-framework/src/tasqsym/core.py --config ./src/tasqsym_samples_more/core_settings.json --btfile ./tasqsym_encoder_output.json --connection standalone
```

The code will never terminate as there are no actual skill implementations for checking whether the goal statement is true or not. However, such a skill could be implemented by using vision-language models (e.g., ask gpt-4o whether the goal statement is true given an image of the environment captured from the robot's camera).