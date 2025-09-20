"""
AI Chatbot API endpoints for user assistance
"""

import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
import requests
import asyncio

from app.shared.database import get_db
from app.dependencies import get_current_active_user
from app.user_management.user_models import User
from app.application_flow.application_models import Application
from app.shared.logging_config import get_logger
from app.config import settings

logger = get_logger(__name__)

router = APIRouter(prefix="/chatbot", tags=["chatbot"])

# Pydantic models
class ChatMessage(BaseModel):
    role: str  # user, assistant, system
    content: str
    timestamp: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class ChatSession(BaseModel):
    session_id: str
    user_id: str
    messages: List[ChatMessage]
    context: Dict[str, Any]
    created_at: str
    updated_at: str

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    stream: bool = False

class ChatResponse(BaseModel):
    session_id: str
    response: str
    suggestions: List[str] = []
    context_updated: bool = False
    processing_time_ms: int
    timestamp: str

class ChatSessionList(BaseModel):
    sessions: List[ChatSession]
    total_count: int

class ChatSettings(BaseModel):
    language: str = "en"
    personality: str = "helpful"  # helpful, formal, friendly
    response_length: str = "medium"  # short, medium, detailed
    include_suggestions: bool = True


# In-memory chat sessions storage (in production, use Redis or database)
chat_sessions: Dict[str, ChatSession] = {}
websocket_connections: Dict[str, WebSocket] = {}


async def call_llm_for_chat(messages: List[ChatMessage], context: Dict[str, Any]) -> Dict[str, Any]:
    """Call Ollama LLM for chat response"""
    try:
        # Build conversation prompt
        conversation_history = ""
        for msg in messages[-10:]:  # Keep last 10 messages for context
            conversation_history += f"{msg.role}: {msg.content}\n"

        # Build system prompt with context
        system_prompt = f"""
You are a helpful AI assistant for the UAE Social Security system. You help users with:
- Understanding benefit eligibility
- Application process guidance
- Document requirements
- Status inquiries
- General support

Current context:
{json.dumps(context, indent=2)}

Guidelines:
- Be helpful, professional, and accurate
- Provide specific information about UAE social security benefits
- If you don't know something, say so and suggest contacting support
- Keep responses concise but informative
- Always be respectful and patient

Conversation history:
{conversation_history}

Provide a helpful response to the user's latest message.
"""

        ollama_request = {
            "model": "qwen2:1.5b",
            "prompt": system_prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "num_predict": 512
            }
        }

        response = requests.post(
            f"{settings.OLLAMA_BASE_URL}/api/generate",
            json=ollama_request,
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            return {
                "success": True,
                "response": result.get("response", "I'm sorry, I couldn't generate a response. Please try again."),
                "suggestions": []
            }
        else:
            logger.error(f"LLM API error: {response.status_code} - {response.text}")
            return {
                "success": False,
                "error": f"LLM API error: {response.status_code}",
                "response": "I'm experiencing technical difficulties. Please try again later or contact support."
            }

    except Exception as e:
        logger.error(f"Error calling LLM for chat: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "response": "I'm sorry, I'm having trouble processing your request right now. Please try again."
        }


def generate_suggestions(user_message: str, context: Dict[str, Any]) -> List[str]:
    """Generate response suggestions based on user message and context"""
    suggestions = []

    message_lower = user_message.lower()

    # Application-related suggestions
    if any(word in message_lower for word in ["apply", "application", "submit"]):
        suggestions.extend([
            "What documents do I need?",
            "How long does processing take?",
            "Can I check my application status?"
        ])

    # Status-related suggestions
    elif any(word in message_lower for word in ["status", "progress", "update"]):
        suggestions.extend([
            "When will I get a decision?",
            "What happens next?",
            "How can I update my information?"
        ])

    # Eligibility-related suggestions
    elif any(word in message_lower for word in ["eligible", "qualify", "requirements"]):
        suggestions.extend([
            "What are the income limits?",
            "Do I qualify for benefits?",
            "What are the age requirements?"
        ])

    # Document-related suggestions
    elif any(word in message_lower for word in ["document", "paper", "upload"]):
        suggestions.extend([
            "How do I upload documents?",
            "What format should documents be?",
            "My document was rejected, why?"
        ])

    # Default suggestions if none match
    else:
        suggestions.extend([
            "How do I apply for benefits?",
            "What documents do I need?",
            "Check application status"
        ])

    return suggestions[:3]  # Return max 3 suggestions


def get_user_context(user: User, db: Session) -> Dict[str, Any]:
    """Build user context for chat"""
    context = {
        "user_id": str(user.id),
        "username": user.username,
        "applications": [],
        "recent_activity": []
    }

    # Get user's applications
    applications = db.query(Application).filter(Application.user_id == user.id).all()
    for app in applications:
        context["applications"].append({
            "id": str(app.id),
            "status": app.status,
            "progress": app.progress,
            "created_at": app.created_at.isoformat() if app.created_at else None
        })

    return context


@router.post("/chat", response_model=ChatResponse,
            summary="Send chat message",
            description="Send message to AI chatbot and get response")
async def chat_message(
    chat_request: ChatRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Send message to chatbot"""
    start_time = datetime.utcnow()

    try:
        # Get or create session
        session_id = chat_request.session_id or f"session_{current_user.id}_{int(start_time.timestamp())}"

        if session_id not in chat_sessions:
            # Create new session
            user_context = get_user_context(current_user, db)
            chat_sessions[session_id] = ChatSession(
                session_id=session_id,
                user_id=str(current_user.id),
                messages=[],
                context=user_context,
                created_at=start_time.isoformat() + "Z",
                updated_at=start_time.isoformat() + "Z"
            )

        session = chat_sessions[session_id]

        # Add user message
        user_message = ChatMessage(
            role="user",
            content=chat_request.message,
            timestamp=start_time.isoformat() + "Z"
        )
        session.messages.append(user_message)

        # Update context if provided
        if chat_request.context:
            session.context.update(chat_request.context)

        # Get AI response
        llm_result = await call_llm_for_chat(session.messages, session.context)

        if llm_result["success"]:
            bot_response = llm_result["response"]
        else:
            bot_response = "I apologize, but I'm having difficulty processing your request right now. Please try again or contact our support team for assistance."

        # Add bot response to session
        bot_message = ChatMessage(
            role="assistant",
            content=bot_response,
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
        session.messages.append(bot_message)

        # Generate suggestions
        suggestions = generate_suggestions(chat_request.message, session.context)

        # Update session
        session.updated_at = datetime.utcnow().isoformat() + "Z"

        # Calculate processing time
        processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        logger.info("Chat message processed",
                   session_id=session_id,
                   user_id=str(current_user.id),
                   message_length=len(chat_request.message),
                   response_length=len(bot_response),
                   processing_time_ms=processing_time)

        return ChatResponse(
            session_id=session_id,
            response=bot_response,
            suggestions=suggestions,
            context_updated=bool(chat_request.context),
            processing_time_ms=processing_time,
            timestamp=start_time.isoformat() + "Z"
        )

    except Exception as e:
        logger.error("Chat message processing failed",
                    user_id=str(current_user.id),
                    session_id=chat_request.session_id,
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "CHAT_FAILED",
                "message": "Failed to process chat message"
            }
        )


@router.get("/sessions", response_model=ChatSessionList,
           summary="Get chat sessions",
           description="Retrieve user's chat sessions")
async def get_chat_sessions(
    current_user: User = Depends(get_current_active_user)
):
    """Get user's chat sessions"""
    try:
        user_sessions = [
            session for session in chat_sessions.values()
            if session.user_id == str(current_user.id)
        ]

        logger.info("Chat sessions retrieved",
                   user_id=str(current_user.id),
                   session_count=len(user_sessions))

        return ChatSessionList(
            sessions=user_sessions,
            total_count=len(user_sessions)
        )

    except Exception as e:
        logger.error("Failed to get chat sessions",
                    user_id=str(current_user.id),
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "SESSIONS_FETCH_FAILED",
                "message": "Failed to retrieve chat sessions"
            }
        )


@router.get("/sessions/{session_id}", response_model=ChatSession,
           summary="Get specific chat session",
           description="Retrieve specific chat session by ID")
async def get_chat_session(
    session_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get specific chat session"""
    try:
        if session_id not in chat_sessions:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "SESSION_NOT_FOUND",
                    "message": "Chat session not found"
                }
            )

        session = chat_sessions[session_id]

        # Check if user owns the session
        if session.user_id != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "SESSION_ACCESS_DENIED",
                    "message": "Access denied to this chat session"
                }
            )

        logger.info("Chat session retrieved",
                   session_id=session_id,
                   user_id=str(current_user.id))

        return session

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get chat session",
                    session_id=session_id,
                    user_id=str(current_user.id),
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "SESSION_FETCH_FAILED",
                "message": "Failed to retrieve chat session"
            }
        )


@router.delete("/sessions/{session_id}",
              summary="Delete chat session",
              description="Delete specific chat session")
async def delete_chat_session(
    session_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Delete chat session"""
    try:
        if session_id not in chat_sessions:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "SESSION_NOT_FOUND",
                    "message": "Chat session not found"
                }
            )

        session = chat_sessions[session_id]

        # Check if user owns the session
        if session.user_id != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "SESSION_ACCESS_DENIED",
                    "message": "Access denied to this chat session"
                }
            )

        # Delete session
        del chat_sessions[session_id]

        # Close websocket connection if exists
        if session_id in websocket_connections:
            await websocket_connections[session_id].close()
            del websocket_connections[session_id]

        logger.info("Chat session deleted",
                   session_id=session_id,
                   user_id=str(current_user.id))

        return {"message": "Chat session deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete chat session",
                    session_id=session_id,
                    user_id=str(current_user.id),
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "SESSION_DELETE_FAILED",
                "message": "Failed to delete chat session"
            }
        )


@router.websocket("/ws/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time chat"""
    await websocket.accept()

    try:
        # Store connection
        websocket_connections[session_id] = websocket

        logger.info("WebSocket connection established", session_id=session_id)

        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)

            # Process message (simplified - in production, add proper auth)
            response = {
                "type": "message",
                "content": f"Echo: {message_data.get('message', '')}",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }

            # Send response
            await websocket.send_text(json.dumps(response))

    except WebSocketDisconnect:
        logger.info("WebSocket connection closed", session_id=session_id)
        if session_id in websocket_connections:
            del websocket_connections[session_id]
    except Exception as e:
        logger.error("WebSocket error", session_id=session_id, error=str(e))
        if session_id in websocket_connections:
            del websocket_connections[session_id]


@router.get("/quick-help", summary="Get quick help responses")
async def get_quick_help():
    """Get quick help responses for common questions"""
    quick_help = {
        "application_process": {
            "question": "How do I apply for benefits?",
            "answer": "You can apply online through our portal. You'll need your Emirates ID, salary certificate, and bank statements. The process takes about 10 minutes to complete."
        },
        "document_requirements": {
            "question": "What documents do I need?",
            "answer": "Required documents: Emirates ID, salary certificate (last 3 months), bank statements (last 6 months), and passport-size photograph."
        },
        "processing_time": {
            "question": "How long does processing take?",
            "answer": "Most applications are processed within 2-3 business days. Complex cases may take up to 7 business days. You'll receive updates via SMS and email."
        },
        "eligibility_criteria": {
            "question": "Am I eligible for benefits?",
            "answer": "Basic eligibility: UAE citizen or resident, monthly income below AED 5,000, bank balance below AED 50,000, age 18-65. Additional criteria may apply."
        },
        "status_check": {
            "question": "How can I check my application status?",
            "answer": "Log into your account and visit the 'My Applications' section. You can also call our hotline at +971-4-123-4567."
        }
    }

    return quick_help


@router.get("/health", summary="Chatbot service health check")
async def chatbot_health_check():
    """Check chatbot service health"""
    try:
        # Test LLM connectivity
        test_messages = [
            ChatMessage(role="user", content="Hello", timestamp=datetime.utcnow().isoformat() + "Z")
        ]
        llm_result = await call_llm_for_chat(test_messages, {})

        return {
            "status": "healthy",
            "service": "Chatbot",
            "llm_available": llm_result["success"],
            "active_sessions": len(chat_sessions),
            "websocket_connections": len(websocket_connections),
            "supported_languages": ["en", "ar"],
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

    except Exception as e:
        logger.error(f"Chatbot health check failed: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "service": "Chatbot",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        )