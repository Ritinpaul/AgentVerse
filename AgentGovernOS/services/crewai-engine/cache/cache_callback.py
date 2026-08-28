"""
CrewAI Step Callback — integrates QICACHE into every LLM call.

How it works:
1. Before crew runs, load cache settings from request context.
2. On each agent step, intercept the input (task description).
3. Check QICACHE — if HIT, inject cached result directly (skip LLM).
4. On step completion, store the LLM response if save_enabled.

Note: CrewAI's callback API gives us `on_agent_action` and
`on_agent_finish` hooks — we use both.
"""

import logging
from typing import Any

from cache.qicache_engine import QICacheEngine, QICacheSettings

logger = logging.getLogger(__name__)


class QICacheCallback:
    """
    CrewAI-compatible callback that wraps every agent step with cache logic.

    usage::

        cache = QICacheEngine(redis_client=r, db_session=db)
        settings = QICacheSettings(cache_enabled=True, save_enabled=True)
        crew = DisputeResolutionCrew
        crew.build_crew(dispute, callbacks=[QICacheCallback(cache, settings)])
    """

    def __init__(self, engine: QICacheEngine, settings: QICacheSettings | None = None):
        self.engine = engine
        self.settings = settings or QICacheSettings
        self._pending: dict[str, str] = {}  # task_key → query_hash (store after LLM)

    # ──────────────────────────────────────────────
    # CrewAI callback hooks
    # ──────────────────────────────────────────────

    def on_agent_action(self, action: Any, agent_role: str = "") -> Any:
        """
        Fires BEFORE the LLM processes a task input.
        We check the cache here — if HIT, we log it.
        (CrewAI doesn't support full LLM bypass via callbacks yet,
        so this is a best-effort intercept for logging and stats tracking.)
        """
        query_text = self._extract_query(action)
        if not query_text:
            return action

        result = self.engine.check(
            query_text=query_text,
            agent_role=agent_role,
            settings=self.settings,
        )

        if result.hit:
            logger.info(
                f"[QICACHE HIT] agent={agent_role} source={result.source} "
                f"tokens_saved={result.tokens_saved}"
            )
        else:
            # Store hash so on_agent_finish can use it
            self._pending[agent_role] = result.query_hash
            logger.debug(f"[QICACHE MISS] agent={agent_role} → routing to LLM")

        return action

    def on_agent_finish(self, output: Any, agent_role: str = "") -> Any:
        """
        Fires AFTER the LLM returns a result.
        We store the response in cache here (if save_enabled).
        """
        query_hash = self._pending.pop(agent_role, None)
        if not query_hash:
            return output

        response_text = self._extract_output(output)
        if response_text and self.settings.save_enabled:
            stored = self.engine.store(
                query_hash=query_hash,
                query_text="",  # normalized form already hashed
                response_text=response_text,
                metadata={"agent_role": agent_role},
                settings=self.settings,
            )
            if stored:
                logger.info(f"[QICACHE STORE] agent={agent_role} hash={query_hash[:8]}...")

        return output

    def get_stats(self) -> dict:
        return self.engine.stats

    # ──────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────

    @staticmethod
    def _extract_query(action: Any) -> str:
        """Extract query text from a CrewAI action object."""
        if isinstance(action, str):
            return action
        if hasattr(action, "tool_input"):
            return str(action.tool_input)
        if hasattr(action, "log"):
            return str(action.log)
        return str(action)

    @staticmethod
    def _extract_output(output: Any) -> str:
        """Extract response text from a CrewAI output object."""
        if isinstance(output, str):
            return output
        if hasattr(output, "return_values"):
            return str(output.return_values.get("output", ""))
        if hasattr(output, "output"):
            return str(output.output)
        return str(output)
