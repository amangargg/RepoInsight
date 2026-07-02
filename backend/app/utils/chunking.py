from langchain_text_splitters import RecursiveCharacterTextSplitter, Language

def get_splitter_for_language(language: str) -> RecursiveCharacterTextSplitter:
    """Return an appropriate syntax-aware splitter based on file extension."""
    lang_enum = None
    if language == 'py':
        lang_enum = Language.PYTHON
    elif language in ('js', 'jsx', 'ts', 'tsx'):
        lang_enum = Language.JS
    elif language in ('html', 'htm'):
        lang_enum = Language.HTML
    elif language in ('cpp', 'cc', 'h', 'hpp'):
        lang_enum = Language.CPP
    elif language == 'java':
        lang_enum = Language.JAVA

    if lang_enum:
        return RecursiveCharacterTextSplitter.from_language(
            language=lang_enum,
            chunk_size=1200,
            chunk_overlap=200
        )
    
    # Generic text splitter
    return RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150
    )
