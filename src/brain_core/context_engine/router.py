from fastapi import APIRouter, Depends
from src.brain_core.context_engine.schemas import ContextAssemblyRequest, AssembledContext
from src.brain_core.context_engine.assembler import ContextAssembler

router = APIRouter(prefix="/api/v1/context", tags=["Context Engine"])

def get_context_assembler() -> ContextAssembler:
    return ContextAssembler()

@router.post("/assemble", response_model=AssembledContext)
async def assemble_context(
    request: ContextAssemblyRequest, 
    assembler: ContextAssembler = Depends(get_context_assembler)
):
    """
    Assembles a grounded context object by aggregating data from Business Systems 
    and Memory Framework.
    """
    return await assembler.assemble_context(request)
