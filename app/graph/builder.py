from langgraph.graph import END, START, StateGraph

from app.graph.nodes.handlers import (
    append_image_message_node,
    behavior_decision_node,
    behavior_route,
    image_judgment_node,
    image_route,
    load_context_node,
    memory_extraction_node,
    prepare_advance_node,
    prepare_avoid_node,
    prepare_normal_node,
    prepare_photo_node,
    reply_generation_node,
    scene_judgment_node,
    state_update_node,
    tts_generation_node,
    voice_judgment_node,
    voice_route,
)
from app.graph.runtime import GraphRuntime
from app.graph.schemas import ChatState


def build_graph(runtime: GraphRuntime):
    async def load_context(state: ChatState):
        return await load_context_node(runtime, state)

    async def behavior_decision(state: ChatState):
        return await behavior_decision_node(runtime, state)

    async def reply_generation(state: ChatState):
        return await reply_generation_node(runtime, state)

    async def memory_extraction(state: ChatState):
        return await memory_extraction_node(runtime, state)

    async def image_judgment(state: ChatState):
        return image_judgment_node(runtime, state)

    async def voice_judgment(state: ChatState):
        return voice_judgment_node(runtime, state)

    async def tts_generation(state: ChatState):
        return await tts_generation_node(runtime, state)

    graph = StateGraph(ChatState)
    graph.add_node("load_context", load_context)
    graph.add_node("behavior_decision", behavior_decision)
    graph.add_node("prepare_normal", prepare_normal_node)
    graph.add_node("prepare_avoid", prepare_avoid_node)
    graph.add_node("prepare_advance", prepare_advance_node)
    graph.add_node("prepare_photo", prepare_photo_node)
    graph.add_node("scene_judgment", scene_judgment_node)
    graph.add_node("reply_generation", reply_generation)
    graph.add_node("image_judgment", image_judgment)
    graph.add_node("append_image_message", append_image_message_node)
    graph.add_node("voice_judgment", voice_judgment)
    graph.add_node("tts_generation", tts_generation)
    graph.add_node("state_update", state_update_node)
    graph.add_node("memory_extraction", memory_extraction)

    graph.add_edge(START, "load_context")
    graph.add_edge("load_context", "behavior_decision")
    graph.add_conditional_edges(
        "behavior_decision",
        behavior_route,
        {
            "normal": "prepare_normal",
            "avoid": "prepare_avoid",
            "advance": "prepare_advance",
            "photo_request": "prepare_photo",
        },
    )
    for node in ("prepare_normal", "prepare_avoid", "prepare_advance", "prepare_photo"):
        graph.add_edge(node, "scene_judgment")
    graph.add_edge("scene_judgment", "reply_generation")
    graph.add_edge("reply_generation", "image_judgment")
    graph.add_conditional_edges(
        "image_judgment",
        image_route,
        {"send": "append_image_message", "no_image": "voice_judgment"},
    )
    graph.add_edge("append_image_message", "voice_judgment")
    graph.add_conditional_edges(
        "voice_judgment",
        voice_route,
        {"send": "tts_generation", "no_voice": "state_update"},
    )
    graph.add_edge("tts_generation", "state_update")
    graph.add_edge("state_update", "memory_extraction")
    graph.add_edge("memory_extraction", END)
    return graph.compile()
