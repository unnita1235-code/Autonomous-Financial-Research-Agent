import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VerifyImports")

def test_imports():
    modules_to_test = [
        "agent.core",
        "agent.errorhandler",
        "agent.circuitbreaker",
        "agent.queryanalyzer",
        "memory.episodic",
        "memory.vector_store",
        "synthesis.engine",
        "evaluation.metrics",
        "tools"
    ]
    
    failed = False
    for mod in modules_to_test:
        try:
            __import__(mod)
            logger.info(f"✅ Successfully imported {mod}")
        except ImportError as e:
            logger.error(f"❌ Failed to import {mod}: {e}")
            failed = True
        except Exception as e:
            logger.error(f"⚠️ Unexpected error importing {mod}: {e}")
            failed = True
            
    if failed:
        logger.error("Build Verification FAILED")
        sys.exit(1)
    else:
        logger.info("Build Verification PASSED")
        sys.exit(0)

if __name__ == "__main__":
    # Add root to path
    import os
    sys.path.append(os.getcwd())
    test_imports()
