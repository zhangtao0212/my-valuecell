import asyncio
import logging
from datetime import datetime, date, timezone
from typing import List, Dict, Any, Optional, AsyncGenerator
import re

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, MessagesState, START, END
from pydantic import BaseModel, Field, field_validator
from valuecell.core.agent.decorator import create_wrapped_agent
from valuecell.core.types import BaseAgent, ComponentType, ReportComponentData
from valuecell.core import StreamResponse, streaming

from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

logger = logging.getLogger(__name__)

# Available analysts from TradingAgents
AVAILABLE_ANALYSTS = ["market", "social", "news", "fundamentals"]

# Common stock tickers for demo
COMMON_TICKERS = {
    "AAPL": "Apple Inc.",
    "GOOGL": "Alphabet Inc.",
    "MSFT": "Microsoft Corporation", 
    "NVDA": "NVIDIA Corporation",
    "TSLA": "Tesla Inc.",
    "AMZN": "Amazon.com Inc.",
    "META": "Meta Platforms Inc.",
    "NFLX": "Netflix Inc.",
    "BABA": "Alibaba Group Holding Limited",
    "BIDU": "Baidu Inc.",
    "JD": "JD.com Inc.",
    "PDD": "Pinduoduo Inc.",
    "WB": "Weibo Corporation",
    "TME": "Tencent Music Entertainment Group",
    "NTES": "NetEase Inc.",
    "BILI": "Bilibili Inc.",
    "YFIN": "Yahoo Finance",
    "TCEHY": "Tencent Holdings Limited",
    "TCOM": "TCOM Inc.",
    "ALIB": "Alibaba Group Holding Limited",
    "WUBA": "58.com Inc.",
    "XOM": "Exxon Mobil Corporation",
    "CVX": "Chevron Corporation",
    "GE": "General Electric Company",
    "BA": "Boeing Company",
    "CAT": "Caterpillar Inc.",
    "CSCO": "Cisco Systems Inc.",
    "DD": "DuPont de Nemours Inc.",
    "HON": "Honeywell International Inc.",
    "IBM": "International Business Machines Corporation",
    "JNJ": "Johnson & Johnson",
    "JPM": "JPMorgan Chase & Co.",
    "KO": "Coca-Cola Company",
    "MCD": "McDonald's Corporation",
    "MMM": "3M Company",
    "NKE": "Nike Inc.",
    "PFE": "Pfizer Inc.",
    "PG": "Procter & Gamble Company",
    "RTX": "Raytheon Technologies Corporation",
    "SBUX": "Starbucks Corporation",
    "UNH": "UnitedHealth Group Inc.",
    "VZ": "Verizon Communications Inc.",
    "WMT": "Walmart Inc.",
    "WBA": "Walgreens Boots Alliance Inc.",
    "XOM": "Exxon Mobil Corporation",
    "AMZN": "Amazon.com Inc.",
    "BAC": "Bank of America Corporation",
    "HOOD": "Robinhood Markets Inc.",
    "META": "Meta Platforms Inc.",
    "DJI": "Dow Jones Industrial Average",
    "SPY": "SPDR S&P 500 ETF"
}

# LLM provider options
LLM_PROVIDERS = {
    "openai": "OpenAI",
    "azure": "Azure OpenAI",
    "anthropic": "Anthropic",
    "google": "Google",
    "ollama": "Ollama",
    "openrouter": "OpenRouter"
}

# Available models for each provider
LLM_MODELS = {
    "openai": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
    "azure": ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "gpt-35-turbo"],  # Azure deployment names, put available ones first
    "anthropic": ["claude-3-5-sonnet-20241022", "claude-3-haiku-20240307"],
    "google": ["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"],
    "ollama": ["llama3.2", "llama3.1", "qwen2.5"],
    "openrouter": ["openai/gpt-4o-mini", "anthropic/claude-3-5-sonnet-20241022", "google/gemini-2.0-flash"]
}


class TradingRequest(BaseModel):
    """Trading analysis request model"""
    ticker: str = Field(
        ...,
        description="Stock ticker symbol to analyze (e.g., AAPL, GOOGL, NVDA)"
    )
    trade_date: Optional[str] = Field(
        default=None,
        description="Date for analysis in YYYY-MM-DD format. If not provided, uses current date."
    )
    selected_analysts: List[str] = Field(
        default=AVAILABLE_ANALYSTS,
        description=f"List of analysts to use for analysis. Available: {AVAILABLE_ANALYSTS}. If empty, all analysts will be used."
    )
    llm_provider: Optional[str] = Field(
        default=None,
        description=f"LLM provider to use. Available: {list(LLM_PROVIDERS.keys())}. If not provided, uses default from config."
    )
    deep_think_model: Optional[str] = Field(
        default=None,
        description="Model for deep thinking tasks. If not provided, uses default from config."
    )
    quick_think_model: Optional[str] = Field(
        default=None,
        description="Model for quick thinking tasks. If not provided, uses default from config."
    )
    debug: bool = Field(
        default=False,
        description="Whether to run in debug mode with detailed tracing"
    )

    @field_validator("ticker")
    @classmethod
    def validate_ticker(cls, v):
        if not v:
            raise ValueError("Ticker symbol is required")
        # Convert to uppercase and remove any whitespace
        ticker = v.upper().strip()
        if not re.match(r'^[A-Z]{1,5}$', ticker):
            raise ValueError(f"Invalid ticker format: {ticker}. Should be 1-5 uppercase letters.")
        return ticker

    @field_validator("trade_date")
    @classmethod
    def validate_trade_date(cls, v):
        if v is None:
            return None
        try:
            datetime.strptime(v, "%Y-%m-%d")
            return v
        except ValueError:
            raise ValueError(f"Invalid date format: {v}. Use YYYY-MM-DD format.")

    @field_validator("selected_analysts")
    @classmethod
    def validate_analysts(cls, v):
        if not v:
            return AVAILABLE_ANALYSTS
        invalid_analysts = set(v) - set(AVAILABLE_ANALYSTS)
        if invalid_analysts:
            raise ValueError(
                f"Invalid analysts: {invalid_analysts}. Available: {AVAILABLE_ANALYSTS}"
            )
        return v

    @field_validator("llm_provider")
    @classmethod
    def validate_llm_provider(cls, v):
        if v is None:
            return None
        if v not in LLM_PROVIDERS:
            raise ValueError(
                f"Invalid LLM provider: {v}. Available: {list(LLM_PROVIDERS.keys())}"
            )
        return v


class DialogueState(MessagesState):
    """State for dialogue management"""
    parsed_request: Optional[TradingRequest] = None
    is_help_request: bool = False
    analysis_complete: bool = False
    current_step: str = "parsing"


class TradingAgents(BaseAgent):
    """TradingAgents adapter for valuecell core agent system"""
    
    def __init__(self):
        super().__init__()
        # Initialize LLM for query parsing
        self.parsing_llm = ChatOpenAI(model="gpt-4o", temperature=0)
        
        # Keep track of current trading graph instance
        self._current_graph: Optional[TradingAgentsGraph] = None
        
        # Initialize the dialogue graph
        self.dialogue_graph = self._create_dialogue_graph()
        
    def _create_dialogue_graph(self):
        """Create a LangGraph-based dialogue management graph"""
        
        def parse_query(state: DialogueState):
            """Parse the user query to extract trading parameters"""
            messages = state["messages"]
            if not messages:
                return state
                
            user_query = messages[-1].content
            
            # Check if it's a help request
            if self._is_help_request(user_query):
                return {
                    **state,
                    "is_help_request": True,
                    "current_step": "help"
                }
            
            # Use rule-based parsing instead of LLM to avoid API quota issues
            try:
                logger.info(f"Parsing query using rule-based parser: {user_query}")
                parsed_data = self._rule_based_parse(user_query)
                logger.info(f"Rule-based parsing result: {parsed_data}")
                
                if not parsed_data or "error" in parsed_data:
                    logger.warning(f"Rule-based parser failed: {parsed_data}")
                    return {
                        **state,
                        "current_step": "error"
                    }
                
                # Create TradingRequest object
                trading_request = TradingRequest(**parsed_data)
                logger.info(f"Created TradingRequest: {trading_request}")
                
                return {
                    **state,
                    "parsed_request": trading_request,
                    "current_step": "analysis"
                }
                
            except Exception as e:
                logger.error(f"Error parsing query: {e}", exc_info=True)
                return {
                    **state,
                    "current_step": "error"
                }
        
        def determine_next_step(state: DialogueState):
            """Determine the next step based on parsing results"""
            if state.get("is_help_request"):
                return "provide_help"
            elif state.get("current_step") == "error":
                return "handle_error"
            elif state.get("parsed_request"):
                return "run_analysis"
            else:
                return "handle_error"
        
        # Build the graph
        graph = StateGraph(DialogueState)
        
        # Add nodes
        graph.add_node("parse_query", parse_query)
        graph.add_node("provide_help", lambda state: {**state, "current_step": "complete"})
        graph.add_node("handle_error", lambda state: {**state, "current_step": "complete"})
        graph.add_node("run_analysis", lambda state: {**state, "current_step": "complete"})
        
        # Add edges
        graph.add_edge(START, "parse_query")
        graph.add_conditional_edges("parse_query", determine_next_step, {
            "provide_help": "provide_help",
            "handle_error": "handle_error",
            "run_analysis": "run_analysis"
        })
        graph.add_edge("provide_help", END)
        graph.add_edge("handle_error", END)  
        graph.add_edge("run_analysis", END)
        
        return graph.compile()

    async def stream(
        self, query: str, session_id: str, task_id: str, dependencies: Optional[Dict] = None
    ) -> AsyncGenerator[StreamResponse, None]:
        """Process trading analysis request and stream results"""
        logger.info(f"Processing trading query: {query}. Task ID: {task_id}, Session ID: {session_id}")
        
        try:
            # Initialize dialogue state
            initial_state = DialogueState(
                messages=[HumanMessage(content=query)],
                parsed_request=None,
                is_help_request=False,
                analysis_complete=False,
                current_step="parsing"
            )
            
            # Run the dialogue graph
            final_state = self.dialogue_graph.invoke(initial_state)
            
            # Handle different outcomes
            if final_state.get("is_help_request"):
                help_content = self._generate_help_content()
                yield streaming.message_chunk(help_content)
                yield streaming.done()
                return
            
            if final_state.get("current_step") == "error" or not final_state.get("parsed_request"):
                error_content = (f"❌ Unable to parse query: {query}\n\nPlease try similar format:\n"
                               f"- 'Analyze AAPL stock'\n"
                               f"- 'Use all analysts to analyze NVDA'\n"
                               f"- 'Use GPT-4 to analyze TSLA, date 2024-01-15'\n"
                               f"- 'What are the available stock codes?'\n")
                yield streaming.message_chunk(error_content)
                yield streaming.done()
                return
            
            trading_request = final_state["parsed_request"]
            
            # Set default date if not provided
            if trading_request.trade_date is None:
                trading_request.trade_date = date.today().strftime("%Y-%m-%d")

            # Create custom config based on request
            config = self._create_config(trading_request)
            
            # Yield configuration info
            config_content = (f"🔧 **Configuration information**\n"
                            f"- Stock code: {trading_request.ticker}\n"
                            f"- Analysis date: {trading_request.trade_date}\n"
                            f"- Selected analysts: {', '.join(trading_request.selected_analysts)}\n"
                            f"- LLM provider: {config['llm_provider']}\n"
                            f"- Deep thinking model: {config['deep_think_llm']}\n"
                            f"- Quick thinking model: {config['quick_think_llm']}\n"
                            f"- Debug mode: {'Yes' if trading_request.debug else 'No'}\n\n")
            yield streaming.message_chunk(config_content)

            # Create TradingAgentsGraph instance
            yield streaming.message_chunk("🚀 **Starting to initialize trading analysis system...**\n")

            self._current_graph = TradingAgentsGraph(
                selected_analysts=trading_request.selected_analysts,
                debug=trading_request.debug,
                config=config
            )

            yield streaming.message_chunk("✅ **System initialized, starting analysis...**\n\n")

            # Run the analysis
            final_state, processed_decision = self._current_graph.propagate(
                trading_request.ticker, 
                trading_request.trade_date
            )

            # Stream the results
            for result in self._stream_analysis_results(
                trading_request, final_state, processed_decision
            ):
                yield result

        except Exception as e:
            logger.error(f"Error in trading analysis: {e}", exc_info=True)
            error_content = (f"❌ **Error in analysis process**: {str(e)}\n\n"
                           f"Please check parameters and try again. If you need help, please enter 'help' or 'help'.")
            yield streaming.message_chunk(error_content)
            yield streaming.done()

    def _rule_based_parse(self, query: str) -> dict:
        """Rule-based query parsing to extract trading parameters"""
        import re
        
        query_lower = query.lower()
        result = {}
        
        # Extract ticker symbol
        ticker = None
        for ticker_symbol in COMMON_TICKERS.keys():
            if ticker_symbol.lower() in query_lower:
                ticker = ticker_symbol
                break
        
        if not ticker:
            return {"error": "Unable to identify stock code"}
        
        result["ticker"] = ticker
        
        # Extract date (YYYY-MM-DD format)
        date_pattern = r'\d{4}-\d{2}-\d{2}'
        date_match = re.search(date_pattern, query)
        if date_match:
            result["trade_date"] = date_match.group()
        
        # Extract analysts
        selected_analysts = []
        if "All Analysts" in query or "全部分析师" in query:
            selected_analysts = AVAILABLE_ANALYSTS
        else:
            for analyst in AVAILABLE_ANALYSTS:
                if analyst in query_lower:
                    selected_analysts.append(analyst)
        
        if selected_analysts:
            result["selected_analysts"] = selected_analysts
        
        # Extract LLM provider
        llm_provider = DEFAULT_CONFIG["llm_provider"]  # Use config default instead of hardcoded
        for provider_key, provider_info in LLM_PROVIDERS.items():
            if provider_key in query_lower or provider_info.lower() in query_lower:
                llm_provider = provider_key
                break
        
        # Special cases for common provider names (only if not already set by explicit provider name)
        if llm_provider == DEFAULT_CONFIG["llm_provider"]:  # Only override if still using default
            if "openai" in query_lower and "azure" not in query_lower:
                llm_provider = "openai"
            elif "claude" in query_lower or "anthropic" in query_lower:
                llm_provider = "anthropic"
            elif "gemini" in query_lower or "google" in query_lower:
                llm_provider = "google"
        
        result["llm_provider"] = llm_provider
        
        # Check for debug mode
        result["debug"] = "调试" in query or "debug" in query_lower
        
        return result

    def _is_help_request(self, query: str) -> bool:
        """Check if the query is asking for help"""
        help_keywords = ['help', '帮助', '可用', 'available', 'options', '选项', 'what', '什么']
        return any(keyword in query.lower() for keyword in help_keywords)

    def _generate_help_content(self) -> str:
        """Generate help content"""
        ticker_list = '\n'.join([f"  - {k}: {v}" for k, v in COMMON_TICKERS.items()])
        analyst_list = '\n'.join([f"  - {a}" for a in AVAILABLE_ANALYSTS])
        provider_list = '\n'.join([f"  - {k}: {v}" for k, v in LLM_PROVIDERS.items()])
        
        return f"""
📚 **TradingAgents usage help**

**🏢 Available stock codes:**
{ticker_list}

**👥 Available analysts:**
{analyst_list}

**🤖 Available LLM providers:**
{provider_list}

**💡 Example queries:**
- "Analyze AAPL stock"
- "Use market and fundamentals analysts to analyze NVDA"
- "Use anthropic provider to analyze TSLA, date 2024-01-15, enable debug mode"
- "Analyze SPY, use all analysts"

**📝 Query format hints:**
- Stock code: Must be a valid stock code (e.g., AAPL, NVDA)
- Date format: YYYY-MM-DD (optional, default today)
- Analysts: Can choose one or more, default using all
- LLM provider: Optional, default using OpenAI
- Debug mode: Optional, display detailed analysis process

If you have any other questions, please feel free to ask!
"""

    def _create_config(self, request: TradingRequest) -> Dict[str, Any]:
        """Create configuration based on trading request"""
        config = DEFAULT_CONFIG.copy()
        
        if request.llm_provider:
            config["llm_provider"] = request.llm_provider
            
        if request.deep_think_model:
            config["deep_think_llm"] = request.deep_think_model
        elif request.llm_provider and request.llm_provider != DEFAULT_CONFIG["llm_provider"]:
            # Only override if provider changed and model list available
            if request.llm_provider in LLM_MODELS:
                config["deep_think_llm"] = LLM_MODELS[request.llm_provider][0]
        # else keep DEFAULT_CONFIG["deep_think_llm"]
            
        if request.quick_think_model:
            config["quick_think_llm"] = request.quick_think_model
        elif request.llm_provider and request.llm_provider != DEFAULT_CONFIG["llm_provider"]:
            # Only override if provider changed and model list available
            if request.llm_provider in LLM_MODELS:
                config["quick_think_llm"] = LLM_MODELS[request.llm_provider][0]
        # else keep DEFAULT_CONFIG["quick_think_llm"]
            
        return config

    def _stream_analysis_results(self, request: TradingRequest, final_state: Dict, processed_decision: str):
        """Stream analysis results"""
        
        # Market Analysis
        if final_state.get("market_report"):
            yield streaming.message_chunk(f"📈 **Market analysis report**\n")
            report_data = ReportComponentData(
                title="Market Analysis Report",
                data=final_state['market_report'],
                url=None,
                create_time=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            )
            yield streaming.component_generator(report_data.model_dump_json(), ComponentType.REPORT)

        # Sentiment Analysis  
        if final_state.get("sentiment_report"):
            yield streaming.message_chunk(f"😊 **Sentiment analysis report**\n")
            report_data = ReportComponentData(
                title="Sentiment Analysis Report",
                data=final_state['sentiment_report'],
                url=None,
                create_time=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            )
            yield streaming.component_generator(report_data.model_dump_json(), ComponentType.REPORT)

        # News Analysis
        if final_state.get("news_report"):
            yield streaming.message_chunk(f"📰 **News analysis report**\n")
            report_data = ReportComponentData(
                title="News Analysis Report",
                data=final_state['news_report'],
                url=None,
                create_time=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            )
            yield streaming.component_generator(report_data.model_dump_json(), ComponentType.REPORT)

        # Fundamentals Analysis
        if final_state.get("fundamentals_report"):
            yield streaming.message_chunk(f"📊 **Fundamentals analysis report**\n")
            report_data = ReportComponentData(
                title="Fundamentals Analysis Report",
                data=final_state['fundamentals_report'],
                url=None,
                create_time=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            )
            yield streaming.component_generator(report_data.model_dump_json(), ComponentType.REPORT)

        # Investment Debate Results
        if final_state.get("investment_debate_state", {}).get("judge_decision"):
            yield streaming.message_chunk(f"⚖️ **Investment debate results**\n{final_state['investment_debate_state']['judge_decision']}\n\n")

        # Trader Decision
        if final_state.get("trader_investment_plan"):
            yield streaming.message_chunk(f"💼 **Trader investment plan**\n{final_state['trader_investment_plan']}\n\n")

        # Risk Management
        if final_state.get("risk_debate_state", {}).get("judge_decision"):
            yield streaming.message_chunk(f"⚠️ **Risk management assessment**\n{final_state['risk_debate_state']['judge_decision']}\n\n")

        # Final Investment Plan
        if final_state.get("investment_plan"):
            yield streaming.message_chunk(f"📋 **Final investment plan**\n{final_state['investment_plan']}\n\n")

        # Final Decision
        if final_state.get("final_trade_decision"):
            yield streaming.message_chunk(f"🎯 **Final trade decision**\n{final_state['final_trade_decision']}\n\n")

        # Processed Signal
        if processed_decision:
            yield streaming.message_chunk(f"🚦 **Processed trade signal**\n{processed_decision}\n\n")

        # Summary
        summary_content = (f"✅ **Analysis completed**\n\n"
                          f"Stock {request.ticker} on {request.trade_date} analysis completed.\n"
                          f"Used analysts: {', '.join(request.selected_analysts)}\n\n"
                          f"If you need to re-analyze or analyze other stocks, please send a new query.")
        yield streaming.message_chunk(summary_content)
        yield streaming.done()


if __name__ == "__main__":
    agent = create_wrapped_agent(TradingAgents)
    asyncio.run(agent.serve())
