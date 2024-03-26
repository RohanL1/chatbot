import os
import boto3
from langchain.chains import ConversationChain
from langchain.llms.bedrock import Bedrock
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate

# Initialize the DynamoDB client
dynamodb = boto3.client('dynamodb', region_name='us-east-1')

# Define the DynamoDB table name
table_name = 'LlmResponseStore'


# Check if the table exists, and create it if it doesn't
def create_table_if_not_exists():
    try:
        # Check if the table exists
        dynamodb.describe_table(TableName=table_name)
    except dynamodb.exceptions.ResourceNotFoundException:
        # Table doesn't exist, create it
        dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'question',
                    'KeyType': 'HASH'  # Partition key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'question',
                    'AttributeType': 'S'  # String
                }
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )
        print("Table created successfully")
        
# Function to store question and answer in DynamoDB
def store_question_answer(question, answer):
    try:
        # Put item into the DynamoDB table
        response = dynamodb.put_item(
            TableName=table_name,
            Item={
                'question': {'S': question['question']},
                'answer': {'S': answer['answer']['response']}
            }
        )
        print("Item stored successfully:", response)
    except Exception as e:
        print("Error storing item:", e)
        

def bedrock_chain():
    # profile = os.environ["AWS_PROFILE"]

    bedrock_runtime = boto3.client(
        service_name="bedrock-runtime",
        region_name="us-east-1",
    )

    titan_llm = Bedrock(
        model_id="amazon.titan-text-express-v1", client=bedrock_runtime, #credentials_profile_name=profile
    )
    titan_llm.model_kwargs = {"temperature": 0.5, "maxTokenCount": 700}

    prompt_template = """System: The following is a friendly conversation between a knowledgeable helpful assistant and a customer.
    The assistant is talkative and provides lots of specific details from it's context.

    Current conversation:
    {history}

    User: {input}
    Bot:"""
    PROMPT = PromptTemplate(
        input_variables=["history", "input"], template=prompt_template
    )

    memory = ConversationBufferMemory(human_prefix="User", ai_prefix="Bot")
    conversation = ConversationChain(
        prompt=PROMPT,
        llm=titan_llm,
        verbose=True,
        memory=memory,
    )

    return conversation


def run_chain(chain, prompt):
    num_tokens = chain.llm.get_num_tokens(prompt)
    return chain({"input": prompt}), num_tokens


def clear_memory(chain):
    return chain.memory.clear()