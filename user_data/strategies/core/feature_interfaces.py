"""
Core Layer - Feature Engineering Interfaces (ISP Compliance)
=============================================================
Plugin-based feature generation (OCP via Strategy Pattern)

Design Philosophy:
- Each feature generator = single responsibility
- Add new features WITHOUT modifying existing code
- Composable: Chain multiple generators
"""
from abc import ABC, abstractmethod
from typing import Dict, Any
from pandas import DataFrame
import logging

logger = logging.getLogger(__name__)


class IFeatureGenerator(ABC):
    """
    Base interface for feature generators (ISP).
    
    OCP: New feature = new class implementing this interface
    SRP: Each generator handles ONE type of feature
    LSP: All generators interchangeable
    
    Complexity: O(n) where n = dataframe rows (unavoidable for TA)
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Args:
            config: Generator-specific configuration
        """
        self.config = config or {}
        self.enabled = self.config.get('enabled', True)
    
    @abstractmethod
    def generate(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Generate features and add to dataframe.
        
        Args:
            dataframe: OHLCV data
            metadata: Pair metadata (pair name, timeframe, etc.)
        
        Returns:
            DataFrame with new feature columns added
            
        Time: O(n) minimum (must iterate rows)
        Memory: O(m) where m = new columns added
        """
        pass
    
    @abstractmethod
    def get_feature_names(self) -> list[str]:
        """
        List feature column names this generator creates.
        
        Used for:
        1. Documentation
        2. Feature importance analysis
        3. Debugging
        
        Time: O(1)
        """
        pass
    
    def validate_dataframe(self, dataframe: DataFrame) -> bool:
        """
        Check if dataframe has required columns.
        
        Override this if your generator needs specific columns.
        
        Time: O(1) - just column name checks
        """
        required = ['open', 'high', 'low', 'close', 'volume']
        missing = [col for col in required if col not in dataframe.columns]
        
        if missing:
            logger.error(f"{self.__class__.__name__} missing columns: {missing}")
            return False
        
        return True


class ICointegrationFeatureGenerator(ABC):
    """
    Specialized interface for pair-based features (cointegration, correlation).
    
    Different from IFeatureGenerator because it needs TWO pairs' data.
    ISP: Don't force single-pair generators to implement pair logic.
    """
    
    @abstractmethod
    def generate_pair_features(
        self, 
        dataframe_x: DataFrame,
        dataframe_y: DataFrame,
        pair_x: str,
        pair_y: str
    ) -> Dict[str, float]:
        """
        Generate features from TWO pairs (statistical arbitrage).
        
        Returns:
            Dict of feature values (not dataframe - these are scalar features)
        """
        pass


class FeaturePipeline:
    """
    Orchestrator for feature generation (Composite Pattern).
    
    Benefits:
    - Sequential execution with error handling
    - Performance tracking per generator
    - Feature importance aggregation
    
    Complexity:
    - Execute: O(n × g) where n=rows, g=generators
    - Memory: O(n × f) where f=total features
    """
    
    def __init__(self, generators: list[IFeatureGenerator]):
        """
        Args:
            generators: List of feature generators (order matters!)
        """
        self.generators = [g for g in generators if g.enabled]
        logger.info(f"✅ FeaturePipeline initialized with {len(self.generators)} generators")
    
    def execute(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Run all generators sequentially (pipeline pattern).
        
        Error Handling: Generator failure doesn't crash pipeline (fault tolerance)
        
        Time: O(n × g) where:
            n = dataframe rows
            g = number of generators
        
        Space: O(n × f) where f = total features added
        """
        result = dataframe.copy()
        
        for generator in self.generators:
            try:
                # Validate before execution
                if not generator.validate_dataframe(result):
                    logger.warning(f"⚠️ Skipping {generator.__class__.__name__} - validation failed")
                    continue
                
                # Execute generator
                result = generator.generate(result, metadata)
                
                feature_count = len(generator.get_feature_names())
                logger.debug(f"✅ {generator.__class__.__name__}: added {feature_count} features")
            
            except Exception as e:
                logger.error(f"❌ {generator.__class__.__name__} failed: {e}")
                # Continue with next generator (graceful degradation)
        
        return result
    
    def get_all_feature_names(self) -> list[str]:
        """
        Aggregate all feature names from generators.
        
        Used for FreqAI's feature_list.
        
        Time: O(g) where g = generators
        """
        all_features = []
        for generator in self.generators:
            all_features.extend(generator.get_feature_names())
        
        return all_features
    
    def add_generator(self, generator: IFeatureGenerator):
        """
        Hot-add generator (OCP: extend without modification).
        
        Time: O(1)
        """
        if generator.enabled:
            self.generators.append(generator)
            logger.info(f"✅ Added generator: {generator.__class__.__name__}")
