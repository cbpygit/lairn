from langchain_core.prompts import PromptTemplate

PT_PARSE_CURRICULUM_STRUCTURE = PromptTemplate(
    template="""
    |SYSTEM|

    # Expert school curriculum interpreter

    You are an expert school curriculum interpreter. Your task is to define what
    subject a given school curriculum document is about and what the overall
    structure of the document is given the preface content of a PDF.
    
    You determine:
      - The school subject the document is about
      - The structure of the document as defined by the table of contents
    
    |USER|

    ## Preface content of the document

    {preface_content}

    ## Response format

    {response_format}
    
    ## Response language
    
    {response_language}

""",
    input_variables=["preface_content", "response_format", "response_language"],
)


PT_SUMMARIZE_CURRICULUM_PAGE = PromptTemplate(
    template="""
    |SYSTEM|

    # Expert school curriculum summarizer

    You are an expert school curriculum summarizer. Your task is to extract the
    most important information from a text section of a detailed school
    curriculum and summarize it in a way that is easy to understand. You should
    determine what skills a student is supposed to have established at what
    point in time. What are the learning objectives and what are the key
    milestones?

    |USER|
    
    ## Overall school subject and structure of the document
    
    {doc_structure}
    
    ## Page number
    
    {page_number}
    
    ## Content of the current page

    {page_content}

    ## Response format

      - Respond as a normal string
      - Be concise and structured
      
    ## Response language
    
    {response_language}

""",
    input_variables=[
        "doc_structure",
        "page_number",
        "page_content",
        "response_language",
    ],
)

PT_WRITE_SUBJECT_OVERVIEW = PromptTemplate(
    template="""
    |SYSTEM|

    # Expert school curriculum summarizer

    You receive an automatically generated summary of the state curriculum for the subject {subject}, which 
    is very detailed. Write a shortened list of learning objectives, separated for grades 1 to 2, and grades 
    3 to 4. Your overview should allow parents who are homeschooling to compare their child's learning 
    progress with the curriculum and derive what should be learned in the coming weeks.

    |USER|

    ## Summary of school subject curriculum
    
    {summary}

    ## Response language

    {response_language}

""",
    input_variables=[
        "subject",
        "summary",
        "response_language",
    ],
)


PT_CURRICULUM_PARSER = PromptTemplate(
    template="""
    |SYSTEM|

    # Curriculum parser

    Convert the given curriculum summary into the output format.

    |USER|

    ## Summary of school subject curriculum

    {summary}
    
    ## Response format

    {response_format}

    ## Response language

    {response_language}

""",
    input_variables=[
        "summary",
        "response_format",
        "response_language",
    ],
)


PT_GENERATE_LEARNING_EXAMPLES = PromptTemplate(
    template="""
    |SYSTEM|

    # Expert home schooling learning assistant

    You receive a curriculum summary for grades {grades} for the subject {subject} which includes a number
    of learning targets. Provide {num_examples} examples for learning and exercising activities that can be
    done in the home schooling context for exactly one of these targets provided to you separately. Make sure
    the examples have a balance between screen and off-screen activities, if possible.

    |USER|

    ## Full school subject curriculum

    {curriculum}
    
    # Section
    
    {section}
    
    ## Learning target: provide examples for this target!
    
    {learning_target}

    ## Response format

    {response_format}

    ## Response language

    {response_language}

""",
    input_variables=[
        "grades",
        "subject",
        "num_examples",
        "curriculum",
        "section",
        "learning_target",
        "response_format",
        "response_language",
    ],
)
