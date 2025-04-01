"""
LangGraph controller for voice agent system.

This module provides graph-based conversation flow management for the
voice agent system, integrating LangGraph with LiveKit Agents.
"""

import logging
from typing import Dict, Any, List, Optional, Union, TypedDict, Literal, Tuple
from pydantic import BaseModel, Field

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.checkpoint import MemorySaver

from livekit.agents import RunContext
from services.voice.base_agent import CustomerData, RunContext_T

# Set up logging
logger = logging.getLogger("graph-controller")
logger.setLevel(logging.INFO)

class ConversationState(TypedDict):
    """The state object maintained by the LangGraph controller."""
    # Core conversation components
    messages: List[Union[HumanMessage, AIMessage, SystemMessage]]
    next_step: Optional[str]
    
    # Customer and session data
    customer_data: Dict[str, Any]
    company_id: str
    active_agent: str
    
    # Flow control and memory
    verification_needed: bool
    verification_attempted: bool
    verification_successful: bool
    
    # Tool results and context
    tool_results: List[Dict[str, Any]]
    knowledge_results: List[Dict[str, Any]]
    sentiment: str

class GraphController:
    """
    LangGraph controller that manages the conversation flow between LiveKit agents.
    
    This controller acts as the brain of the system, using a state graph to determine
    what steps should be taken during the conversation, which agent should be active,
    and what operations should be performed.
    """
    
    def __init__(self, company_id: str):
        """Initialize the controller with company context."""
        self.company_id = company_id
        self.graph = self._build_graph()
        self.memory = MemorySaver()
        logger.info(f"Initialized LangGraph controller for company {company_id}")
    
    def _build_graph(self) -> StateGraph:
        """Build the conversation state graph."""
        # Create the graph builder
        builder = StateGraph(ConversationState)
        
        # Add nodes for the main conversation stages
        builder.add_node("verify_customer", self._verify_customer)
        builder.add_node("analyze_intent", self._analyze_intent)
        builder.add_node("route_to_agent", self._route_to_agent)
        builder.add_node("knowledge_search", self._knowledge_search)
        builder.add_node("analyze_sentiment", self._analyze_sentiment)
        builder.add_node("process_agent_response", self._process_agent_response)
        
        # Define conditional edges for the main flow
        builder.add_conditional_edges(
            "verify_customer",
            self._route_after_verification,
            {
                "knowledge_search": "knowledge_search",
                "analyze_intent": "analyze_intent",
                "process_agent_response": "process_agent_response",
            }
        )
        
        builder.add_conditional_edges(
            "analyze_intent",
            self._route_after_intent,
            {
                "route_to_agent": "route_to_agent",
                "knowledge_search": "knowledge_search",
                "process_agent_response": "process_agent_response",
            }
        )
        
        builder.add_conditional_edges(
            "knowledge_search",
            self._route_after_knowledge,
            {
                "analyze_sentiment": "analyze_sentiment",
                "process_agent_response": "process_agent_response",
            }
        )
        
        builder.add_conditional_edges(
            "analyze_sentiment",
            self._route_after_sentiment,
            {
                "process_agent_response": "process_agent_response",
            }
        )
        
        builder.add_conditional_edges(
            "route_to_agent",
            self._route_after_agent_selection,
            {
                "process_agent_response": "process_agent_response",
            }
        )
        
        builder.add_conditional_edges(
            "process_agent_response",
            self._route_after_response,
            {
                "verify_customer": "verify_customer",
                "analyze_intent": "analyze_intent",
                "knowledge_search": "knowledge_search",
                "analyze_sentiment": "analyze_sentiment",
                "route_to_agent": "route_to_agent",
                "end": END,
            }
        )
        
        # Set entry point
        builder.set_entry_point("analyze_intent")
        
        # Compile and return the graph
        return builder.compile()
    
    def _verify_customer(self, state: ConversationState) -> ConversationState:
        """Verify the customer identity if needed."""
        # Mark that we've attempted verification
        state["verification_attempted"] = True
        
        # In a real implementation, this would use LiveKit agent's verification tools
        # For now, we'll simulate the verification process
        customer_data = state["customer_data"]
        
        # Check if we have enough information to verify
        has_verification_info = (
            customer_data.get("customer_id") and customer_data.get("email")
        )
        
        if has_verification_info:
            # Simulate verification success (in real implementation, call the actual verification)
            state["verification_successful"] = True
            logger.info(f"Customer verification successful for session")
        else:
            # Not enough information to verify
            state["verification_successful"] = False
            
            # Add a message requesting verification information
            verification_request = AIMessage(
                content="To proceed with this request, I'll need to verify your identity. "
                        "Could you please provide your customer ID and email address?"
            )
            state["messages"].append(verification_request)
        
        return state
    
    def _analyze_intent(self, state: ConversationState) -> ConversationState:
        """Analyze customer intent to determine next steps."""
        # Get the latest user message
        messages = state["messages"]
        latest_user_message = next((msg for msg in reversed(messages) 
                                  if isinstance(msg, HumanMessage)), None)
        
        if not latest_user_message:
            # No user message to analyze
            return state
            
        # Check for security-sensitive intents that require verification
        intent_requires_verification = self._intent_requires_verification(
            latest_user_message.content
        )
        
        if intent_requires_verification and not state["verification_successful"]:
            state["verification_needed"] = True
        else:
            state["verification_needed"] = False
        
        # Determine the appropriate agent based on intent
        appropriate_agent = self._determine_appropriate_agent(
            latest_user_message.content,
            current_agent=state["active_agent"]
        )
        
        # Store the determined agent and intent information
        if appropriate_agent != state["active_agent"]:
            state["next_step"] = "route_to_agent"
            state["customer_data"]["suggested_agent"] = appropriate_agent
        
        return state
    
    def _route_to_agent(self, state: ConversationState) -> ConversationState:
        """Route the conversation to the appropriate agent."""
        suggested_agent = state["customer_data"].get("suggested_agent")
        
        if suggested_agent and suggested_agent != state["active_agent"]:
            previous_agent = state["active_agent"]
            state["active_agent"] = suggested_agent
            
            # Add a transition message
            if previous_agent == "greeter":
                transition_message = AIMessage(
                    content=f"I'll connect you with our {suggested_agent} specialist who can better assist you with this."
                )
            else:
                transition_message = AIMessage(
                    content=f"I'm transferring you to our {suggested_agent} specialist for further assistance."
                )
                
            state["messages"].append(transition_message)
            logger.info(f"Routing from {previous_agent} to {suggested_agent}")
        
        return state
    
    def _knowledge_search(self, state: ConversationState) -> ConversationState:
        """Search knowledge base for relevant information."""
        # Get the latest user message
        messages = state["messages"]
        latest_user_message = next((msg for msg in reversed(messages) 
                                  if isinstance(msg, HumanMessage)), None)
        
        if not latest_user_message:
            # No user message to search for
            return state
        
        # In a real implementation, this would call a knowledge base service
        # For now, we'll simulate knowledge results
        query = latest_user_message.content
        
        # Simulate knowledge base search results
        results = [
            {
                "content": f"Relevant information about: {query[:30]}...",
                "source": "Knowledge Base",
                "score": 0.85
            }
        ]
        
        # Store the knowledge results in state
        state["knowledge_results"] = results
        logger.info(f"Knowledge search completed with {len(results)} results")
        
        return state
    
    def _analyze_sentiment(self, state: ConversationState) -> ConversationState:
        """Analyze customer sentiment from recent messages."""
        # Get the recent user messages (up to last 3)
        messages = state["messages"]
        recent_user_messages = [msg.content for msg in reversed(messages) 
                               if isinstance(msg, HumanMessage)][:3]
        
        if not recent_user_messages:
            # No user messages to analyze
            return state
        
        # In a real implementation, this would use a sentiment analysis model
        # For now, we'll use a simple keyword-based approach
        
        # Check for negative sentiment indicators
        negative_keywords = ["frustrated", "angry", "disappointed", "unhappy", "problem", "issue", "terrible"]
        positive_keywords = ["happy", "pleased", "great", "excellent", "good", "thanks", "thank"]
        
        combined_text = " ".join(recent_user_messages).lower()
        
        negative_count = sum(1 for word in negative_keywords if word in combined_text)
        positive_count = sum(1 for word in positive_keywords if word in combined_text)
        
        # Determine sentiment
        if negative_count > positive_count:
            sentiment = "negative"
        elif positive_count > negative_count:
            sentiment = "positive"
        else:
            sentiment = "neutral"
        
        # Update state with sentiment
        state["sentiment"] = sentiment
        state["customer_data"]["sentiment"] = sentiment
        
        logger.info(f"Sentiment analysis: {sentiment}")
        return state
    
    def _process_agent_response(self, state: ConversationState) -> ConversationState:
        """Process the response from the current active agent."""
        # In a real implementation, this would get the response from the LiveKit agent
        # For now, we'll simulate agent responses
        
        active_agent = state["active_agent"]
        latest_user_message = next((msg for msg in reversed(state["messages"]) 
                                   if isinstance(msg, HumanMessage)), None)
        
        if not latest_user_message:
            return state
        
        # Get knowledge results if available
        knowledge_context = ""
        if state["knowledge_results"]:
            knowledge_items = [f"- {item['content']}" for item in state["knowledge_results"]]
            knowledge_context = "Based on our information:\n" + "\n".join(knowledge_items)
        
        # Generate an appropriate response based on the active agent
        response_content = f"[{active_agent.upper()}] "
        
        if state["verification_needed"] and not state["verification_successful"]:
            response_content += "I need to verify your identity first. Could you please provide your customer ID and email address?"
        elif active_agent == "greeter":
            response_content += "Welcome to our customer support! How can I assist you today?"
        elif active_agent == "billing":
            response_content += f"I can help with your billing question. {knowledge_context}"
        elif active_agent == "technical":
            response_content += f"Let me help troubleshoot your technical issue. {knowledge_context}"
        elif active_agent == "general":
            response_content += f"Here's the information you requested. {knowledge_context}"
        elif active_agent == "escalation":
            response_content += "I understand this is a complex issue that needs special handling. I'm here to help resolve this for you."
        
        # Add sentiment-aware response if sentiment is negative
        if state["sentiment"] == "negative":
            response_content += " I understand this is frustrating, and I apologize for the inconvenience. Let's work together to resolve this."
        
        # Create and add the agent's response message
        agent_response = AIMessage(content=response_content)
        state["messages"].append(agent_response)
        
        # Reset next step
        state["next_step"] = None
        
        return state
    
    # Router functions to determine the next node
    def _route_after_verification(self, state: ConversationState) -> Literal["knowledge_search", "analyze_intent", "process_agent_response"]:
        """Determine next step after verification."""
        if state["verification_successful"]:
            # If verification was successful, continue with normal flow
            return "knowledge_search"
        else:
            # If verification failed but was needed, process response first
            return "process_agent_response"
    
    def _route_after_intent(self, state: ConversationState) -> Literal["route_to_agent", "knowledge_search", "process_agent_response"]:
        """Determine next step after intent analysis."""
        if state["verification_needed"]:
            # Need to verify customer before proceeding
            state["next_step"] = "verify_customer"
            return "process_agent_response"
        
        if state["next_step"] == "route_to_agent":
            # Need to route to a different agent
            return "route_to_agent"
        
        # Otherwise, search knowledge base
        return "knowledge_search"
    
    def _route_after_knowledge(self, state: ConversationState) -> Literal["analyze_sentiment", "process_agent_response"]:
        """Determine next step after knowledge search."""
        # Always analyze sentiment after knowledge search
        return "analyze_sentiment"
    
    def _route_after_sentiment(self, state: ConversationState) -> Literal["process_agent_response"]:
        """Determine next step after sentiment analysis."""
        # Always process agent response after sentiment analysis
        return "process_agent_response"
    
    def _route_after_agent_selection(self, state: ConversationState) -> Literal["process_agent_response"]:
        """Determine next step after agent selection."""
        # Always process agent response after selecting an agent
        return "process_agent_response"
    
    def _route_after_response(self, state: ConversationState) -> Literal["verify_customer", "analyze_intent", "knowledge_search", "analyze_sentiment", "route_to_agent", "end"]:
        """Determine next step after agent response."""
        if state["next_step"] == "verify_customer":
            return "verify_customer"
        
        # Default to analyzing intent for the next user message
        # In a real implementation, we would check for conversation end conditions
        return "analyze_intent"
    
    # Helper methods
    def _intent_requires_verification(self, message_text: str) -> bool:
        """Determine if the user intent requires identity verification."""
        security_keywords = ["account", "payment", "billing", "password", "email", 
                           "address", "card", "personal", "subscription"]
        
        return any(keyword in message_text.lower() for keyword in security_keywords)
    
    def _determine_appropriate_agent(self, message_text: str, current_agent: str) -> str:
        """Determine the most appropriate agent based on the message text."""
        message_lower = message_text.lower()
        
        # Define keyword sets for different agent types
        billing_keywords = ["bill", "payment", "charge", "refund", "subscription", "invoice", "price"]
        technical_keywords = ["error", "problem", "not working", "broken", "help me fix", "troubleshoot"]
        escalation_keywords = ["manager", "supervisor", "escalate", "complaint", "disappointed", "frustrated"]
        
        # Count keyword matches
        billing_score = sum(1 for keyword in billing_keywords if keyword in message_lower)
        technical_score = sum(1 for keyword in technical_keywords if keyword in message_lower)
        escalation_score = sum(1 for keyword in escalation_keywords if keyword in message_lower) * 2  # Weight escalation higher
        
        # Determine the highest score
        if escalation_score > 0 and escalation_score >= billing_score and escalation_score >= technical_score:
            return "escalation"
        elif billing_score > technical_score:
            return "billing"
        elif technical_score > billing_score:
            return "technical"
        elif billing_score == 0 and technical_score == 0 and current_agent == "greeter":
            return "general"  # Default to general information
        
        # If no clear winner, stay with current agent
        return current_agent
    
    # Public API
    async def process_message(
        self, 
        user_message: str,
        session_id: str,
        live_context: RunContext_T
    ) -> Dict[str, Any]:
        """
        Process a user message using the LangGraph flow.
        
        Args:
            user_message: The text message from the user
            session_id: Unique identifier for this conversation session
            live_context: The LiveKit RunContext with CustomerData
            
        Returns:
            A dict with the response and other state information
        """
        # Get or initialize state
        try:
            state = self.memory.get(session_id)
        except:
            # Create new state
            userdata = live_context.userdata
            customer_data = {
                "customer_id": userdata.customer_id,
                "customer_name": userdata.customer_name,
                "email": userdata.customer_email,
                "phone": userdata.customer_phone,
                "verification_status": userdata.verification_status,
                "sentiment": "neutral"
            }
            
            # Initialize with system and greeting messages
            state = ConversationState(
                messages=[
                    SystemMessage(content="Customer support conversation."),
                ],
                next_step=None,
                customer_data=customer_data,
                company_id=self.company_id,
                active_agent="greeter",
                verification_needed=False,
                verification_attempted=False,
                verification_successful=userdata.verification_status,
                tool_results=[],
                knowledge_results=[],
                sentiment="neutral"
            )
        
        # Add the user message to state
        state["messages"].append(HumanMessage(content=user_message))
        
        # Process the message through the graph
        result = self.graph.invoke(state)
        
        # Save the updated state
        self.memory.put(session_id, result)
        
        # Get the AI's response messages (only the new ones)
        ai_messages = [
            msg for msg in result["messages"] 
            if isinstance(msg, AIMessage) and msg not in state["messages"]
        ]
        
        # Get the last AI message if available
        response = ai_messages[-1].content if ai_messages else "I'm processing your request."
        
        # Update the LiveKit context with information from our graph state
        live_context.userdata.verification_status = result["verification_successful"]
        live_context.userdata.sentiment = result["sentiment"]
        
        # Also update the suggested agent if routing occurred
        if result["active_agent"] != state["active_agent"]:
            suggested_agent = result["active_agent"]
            live_context.userdata.issue_type = suggested_agent
        
        return {
            "response": response,
            "active_agent": result["active_agent"],
            "sentiment": result["sentiment"],
            "verification_status": result["verification_successful"]
        }
    
    async def create_session(self, live_context: RunContext_T) -> str:
        """Create a new session with the graph controller."""
        # Generate a unique session ID
        session_id = f"{self.company_id}_{live_context.userdata.customer_id or 'anonymous'}_{hash(str(live_context))}"
        
        # Initialize state will be created on first message
        logger.info(f"Created new graph session {session_id}")
        return session_id 