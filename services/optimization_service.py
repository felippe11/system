import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Callable
import multiprocessing as mp
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
import time
import logging
from functools import lru_cache, wraps
import pickle
import hashlib
import os
from datetime import datetime, timedelta
import psutil
from memory_profiler import profile
import gc

class OptimizationService:
    """Serviço para otimização de processamento de planilhas e operações pesadas"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Configurações de otimização
        self.config = {
            'chunk_size': 1000,  # Tamanho do chunk para processamento
            'max_workers': min(mp.cpu_count(), 8),  # Máximo de workers
            'cache_ttl': 3600,  # TTL do cache em segundos
            'memory_threshold': 0.8,  # Limite de memória (80%)
            'enable_parallel': True,
            'enable_cache': True,
            'enable_compression': True
        }
        
        # Cache em memória
        self.memory_cache = {}
        self.cache_timestamps = {}
        
        # Diretório de cache em disco
        self.cache_dir = 'cache/optimization'
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Métricas de performance
        self.performance_metrics = {
            'total_operations': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'parallel_operations': 0,
            'processing_times': []
        }
    
    def optimize_dataframe_processing(self, df: pd.DataFrame, 
                                    operation: Callable, 
                                    operation_name: str = "operation",
                                    **kwargs) -> Any:
        """Otimiza processamento de DataFrame usando chunking e paralelização"""
        start_time = time.time()
        
        try:
            # Verificar cache primeiro
            if self.config['enable_cache']:
                cache_key = self._generate_cache_key(df, operation_name, kwargs)
                cached_result = self._get_from_cache(cache_key)
                if cached_result is not None:
                    self.performance_metrics['cache_hits'] += 1
                    self.logger.info(f"Cache hit para {operation_name}")
                    return cached_result
                
                self.performance_metrics['cache_misses'] += 1
            
            # Verificar uso de memória
            if self._check_memory_usage() > self.config['memory_threshold']:
                self.logger.warning("Alto uso de memória detectado, executando limpeza")
                self._cleanup_memory()
            
            # Decidir estratégia de processamento
            if (len(df) > self.config['chunk_size'] * 2 and 
                self.config['enable_parallel']):
                result = self._process_parallel(df, operation, **kwargs)
                self.performance_metrics['parallel_operations'] += 1
            else:
                result = self._process_sequential(df, operation, **kwargs)
            
            # Salvar no cache
            if self.config['enable_cache']:
                self._save_to_cache(cache_key, result)
            
            # Registrar métricas
            processing_time = time.time() - start_time
            self.performance_metrics['total_operations'] += 1
            self.performance_metrics['processing_times'].append(processing_time)
            
            self.logger.info(f"Processamento de {operation_name} concluído em {processing_time:.2f}s")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Erro durante otimização de {operation_name}: {str(e)}")
            raise
    
    def optimize_excel_reading(self, file_path: str, **kwargs) -> pd.DataFrame:
        """Otimiza leitura de arquivos Excel"""
        start_time = time.time()
        
        try:
            # Verificar cache
            file_hash = self._get_file_hash(file_path)
            cache_key = f"excel_read_{file_hash}"
            
            if self.config['enable_cache']:
                cached_df = self._get_from_cache(cache_key)
                if cached_df is not None:
                    self.logger.info(f"Cache hit para leitura de {file_path}")
                    return cached_df
            
            # Otimizações para leitura
            optimized_kwargs = self._optimize_read_parameters(file_path, **kwargs)
            
            # Ler arquivo
            self.logger.info(f"Lendo arquivo Excel: {file_path}")
            df = pd.read_excel(file_path, **optimized_kwargs)
            
            # Otimizar tipos de dados
            df = self._optimize_dtypes(df)
            
            # Salvar no cache
            if self.config['enable_cache']:
                self._save_to_cache(cache_key, df)
            
            processing_time = time.time() - start_time
            self.logger.info(f"Arquivo lido e otimizado em {processing_time:.2f}s")
            
            return df
            
        except Exception as e:
            self.logger.error(f"Erro ao ler arquivo Excel {file_path}: {str(e)}")
            raise
    
    def optimize_csv_reading(self, file_path: str, **kwargs) -> pd.DataFrame:
        """Otimiza leitura de arquivos CSV"""
        start_time = time.time()
        
        try:
            # Verificar cache
            file_hash = self._get_file_hash(file_path)
            cache_key = f"csv_read_{file_hash}"
            
            if self.config['enable_cache']:
                cached_df = self._get_from_cache(cache_key)
                if cached_df is not None:
                    self.logger.info(f"Cache hit para leitura de {file_path}")
                    return cached_df
            
            # Detectar encoding automaticamente
            encoding = self._detect_encoding(file_path)
            kwargs.setdefault('encoding', encoding)
            
            # Otimizações para CSV
            kwargs.setdefault('low_memory', False)
            kwargs.setdefault('dtype', str)  # Ler tudo como string primeiro
            
            # Ler arquivo
            self.logger.info(f"Lendo arquivo CSV: {file_path}")
            df = pd.read_csv(file_path, **kwargs)
            
            # Otimizar tipos de dados
            df = self._optimize_dtypes(df)
            
            # Salvar no cache
            if self.config['enable_cache']:
                self._save_to_cache(cache_key, df)
            
            processing_time = time.time() - start_time
            self.logger.info(f"Arquivo CSV lido e otimizado em {processing_time:.2f}s")
            
            return df
            
        except Exception as e:
            self.logger.error(f"Erro ao ler arquivo CSV {file_path}: {str(e)}")
            raise
    
    def batch_process_with_progress(self, items: List[Any], 
                                  processor: Callable,
                                  batch_size: Optional[int] = None,
                                  progress_callback: Optional[Callable] = None) -> List[Any]:
        """Processa itens em lotes com callback de progresso"""
        if batch_size is None:
            batch_size = self.config['chunk_size']
        
        results = []
        total_items = len(items)
        
        for i in range(0, total_items, batch_size):
            batch = items[i:i + batch_size]
            
            # Processar lote
            if self.config['enable_parallel'] and len(batch) > 10:
                batch_results = self._process_batch_parallel(batch, processor)
            else:
                batch_results = [processor(item) for item in batch]
            
            results.extend(batch_results)
            
            # Callback de progresso
            if progress_callback:
                progress = min((i + batch_size) / total_items, 1.0)
                progress_callback(progress, len(results), total_items)
            
            # Limpeza de memória periódica
            if i % (batch_size * 5) == 0:
                gc.collect()
        
        return results
    
    def _process_parallel(self, df: pd.DataFrame, operation: Callable, **kwargs) -> Any:
        """Processa DataFrame em paralelo usando chunks"""
        chunk_size = self.config['chunk_size']
        chunks = [df[i:i + chunk_size] for i in range(0, len(df), chunk_size)]
        
        with ProcessPoolExecutor(max_workers=self.config['max_workers']) as executor:
            futures = [executor.submit(operation, chunk, **kwargs) for chunk in chunks]
            results = [future.result() for future in as_completed(futures)]
        
        # Combinar resultados
        if isinstance(results[0], pd.DataFrame):
            return pd.concat(results, ignore_index=True)
        elif isinstance(results[0], list):
            combined = []
            for result in results:
                combined.extend(result)
            return combined
        else:
            return results
    
    def _process_sequential(self, df: pd.DataFrame, operation: Callable, **kwargs) -> Any:
        """Processa DataFrame sequencialmente"""
        return operation(df, **kwargs)
    
    def _process_batch_parallel(self, batch: List[Any], processor: Callable) -> List[Any]:
        """Processa lote em paralelo usando threads"""
        with ThreadPoolExecutor(max_workers=min(len(batch), self.config['max_workers'])) as executor:
            futures = [executor.submit(processor, item) for item in batch]
            return [future.result() for future in as_completed(futures)]
    
    def _optimize_dtypes(self, df: pd.DataFrame) -> pd.DataFrame:
        """Otimiza tipos de dados do DataFrame para economizar memória"""
        optimized_df = df.copy()
        
        for col in optimized_df.columns:
            col_type = optimized_df[col].dtype
            
            # Otimizar colunas numéricas
            if col_type == 'int64':
                if optimized_df[col].min() >= 0:
                    if optimized_df[col].max() < 255:
                        optimized_df[col] = optimized_df[col].astype('uint8')
                    elif optimized_df[col].max() < 65535:
                        optimized_df[col] = optimized_df[col].astype('uint16')
                    elif optimized_df[col].max() < 4294967295:
                        optimized_df[col] = optimized_df[col].astype('uint32')
                else:
                    if optimized_df[col].min() > -128 and optimized_df[col].max() < 127:
                        optimized_df[col] = optimized_df[col].astype('int8')
                    elif optimized_df[col].min() > -32768 and optimized_df[col].max() < 32767:
                        optimized_df[col] = optimized_df[col].astype('int16')
                    elif optimized_df[col].min() > -2147483648 and optimized_df[col].max() < 2147483647:
                        optimized_df[col] = optimized_df[col].astype('int32')
            
            # Otimizar colunas de float
            elif col_type == 'float64':
                optimized_df[col] = pd.to_numeric(optimized_df[col], downcast='float')
            
            # Otimizar colunas de string
            elif col_type == 'object':
                # Verificar se pode ser categoria
                unique_ratio = len(optimized_df[col].unique()) / len(optimized_df[col])
                if unique_ratio < 0.5:  # Se menos de 50% são únicos
                    optimized_df[col] = optimized_df[col].astype('category')
        
        return optimized_df
    
    def _optimize_read_parameters(self, file_path: str, **kwargs) -> Dict[str, Any]:
        """Otimiza parâmetros de leitura baseado no arquivo"""
        optimized = kwargs.copy()
        
        # Verificar tamanho do arquivo
        file_size = os.path.getsize(file_path)
        
        # Para arquivos grandes, usar chunks
        if file_size > 50 * 1024 * 1024:  # 50MB
            optimized.setdefault('chunksize', self.config['chunk_size'])
        
        # Otimizações específicas para Excel
        if file_path.endswith(('.xlsx', '.xls')):
            optimized.setdefault('engine', 'openpyxl' if file_path.endswith('.xlsx') else 'xlrd')
        
        return optimized
    
    def _detect_encoding(self, file_path: str) -> str:
        """Detecta encoding do arquivo automaticamente"""
        import chardet
        
        with open(file_path, 'rb') as f:
            sample = f.read(10000)  # Ler amostra
            result = chardet.detect(sample)
            return result['encoding'] or 'utf-8'
    
    def _generate_cache_key(self, df: pd.DataFrame, operation_name: str, kwargs: Dict) -> str:
        """Gera chave única para cache"""
        # Hash do DataFrame (usando shape e algumas amostras)
        df_hash = hashlib.md5(
            f"{df.shape}_{df.columns.tolist()}_{df.head().to_string()}".encode()
        ).hexdigest()[:16]
        
        # Hash dos kwargs
        kwargs_str = str(sorted(kwargs.items()))
        kwargs_hash = hashlib.md5(kwargs_str.encode()).hexdigest()[:8]
        
        return f"{operation_name}_{df_hash}_{kwargs_hash}"
    
    def _get_file_hash(self, file_path: str) -> str:
        """Gera hash do arquivo baseado em modificação e tamanho"""
        stat = os.stat(file_path)
        return hashlib.md5(
            f"{file_path}_{stat.st_mtime}_{stat.st_size}".encode()
        ).hexdigest()[:16]
    
    def _get_from_cache(self, cache_key: str) -> Any:
        """Recupera item do cache"""
        # Verificar cache em memória primeiro
        if cache_key in self.memory_cache:
            timestamp = self.cache_timestamps.get(cache_key, 0)
            if time.time() - timestamp < self.config['cache_ttl']:
                return self.memory_cache[cache_key]
            else:
                # Cache expirado
                del self.memory_cache[cache_key]
                del self.cache_timestamps[cache_key]
        
        # Verificar cache em disco
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.pkl")
        if os.path.exists(cache_file):
            try:
                # Verificar se não expirou
                file_age = time.time() - os.path.getmtime(cache_file)
                if file_age < self.config['cache_ttl']:
                    with open(cache_file, 'rb') as f:
                        data = pickle.load(f)
                        # Salvar em memória para próximas consultas
                        self.memory_cache[cache_key] = data
                        self.cache_timestamps[cache_key] = time.time()
                        return data
                else:
                    # Arquivo expirado
                    os.remove(cache_file)
            except Exception as e:
                self.logger.warning(f"Erro ao ler cache {cache_key}: {str(e)}")
                if os.path.exists(cache_file):
                    os.remove(cache_file)
        
        return None
    
    def _save_to_cache(self, cache_key: str, data: Any) -> None:
        """Salva item no cache"""
        try:
            # Salvar em memória
            self.memory_cache[cache_key] = data
            self.cache_timestamps[cache_key] = time.time()
            
            # Salvar em disco se configurado
            if self.config['enable_compression']:
                cache_file = os.path.join(self.cache_dir, f"{cache_key}.pkl")
                with open(cache_file, 'wb') as f:
                    pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)
        
        except Exception as e:
            self.logger.warning(f"Erro ao salvar cache {cache_key}: {str(e)}")
    
    def _check_memory_usage(self) -> float:
        """Verifica uso atual de memória"""
        return psutil.virtual_memory().percent / 100.0
    
    def _cleanup_memory(self) -> None:
        """Limpa memória e cache"""
        # Limpar cache em memória
        cache_size = len(self.memory_cache)
        self.memory_cache.clear()
        self.cache_timestamps.clear()
        
        # Forçar garbage collection
        gc.collect()
        
        self.logger.info(f"Limpeza de memória executada. {cache_size} itens removidos do cache.")
    
    def clear_cache(self, older_than_hours: Optional[int] = None) -> Dict[str, int]:
        """Limpa cache baseado na idade"""
        cleared_memory = 0
        cleared_disk = 0
        
        cutoff_time = time.time()
        if older_than_hours:
            cutoff_time -= older_than_hours * 3600
        
        # Limpar cache em memória
        keys_to_remove = []
        for key, timestamp in self.cache_timestamps.items():
            if timestamp < cutoff_time:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            if key in self.memory_cache:
                del self.memory_cache[key]
                cleared_memory += 1
            if key in self.cache_timestamps:
                del self.cache_timestamps[key]
        
        # Limpar cache em disco
        for filename in os.listdir(self.cache_dir):
            if filename.endswith('.pkl'):
                file_path = os.path.join(self.cache_dir, filename)
                if os.path.getmtime(file_path) < cutoff_time:
                    try:
                        os.remove(file_path)
                        cleared_disk += 1
                    except Exception as e:
                        self.logger.warning(f"Erro ao remover cache {filename}: {str(e)}")
        
        return {
            'cleared_memory_items': cleared_memory,
            'cleared_disk_files': cleared_disk
        }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Retorna métricas de performance"""
        metrics = self.performance_metrics.copy()
        
        # Calcular estatísticas
        if metrics['processing_times']:
            metrics['avg_processing_time'] = np.mean(metrics['processing_times'])
            metrics['min_processing_time'] = np.min(metrics['processing_times'])
            metrics['max_processing_time'] = np.max(metrics['processing_times'])
        
        # Cache hit rate
        total_cache_requests = metrics['cache_hits'] + metrics['cache_misses']
        if total_cache_requests > 0:
            metrics['cache_hit_rate'] = metrics['cache_hits'] / total_cache_requests * 100
        else:
            metrics['cache_hit_rate'] = 0
        
        # Informações do sistema
        metrics['memory_usage'] = self._check_memory_usage() * 100
        metrics['cpu_count'] = mp.cpu_count()
        metrics['cache_size'] = len(self.memory_cache)
        
        return metrics
    
    def optimize_configuration(self, workload_profile: str = 'balanced') -> None:
        """Otimiza configuração baseada no perfil de workload"""
        if workload_profile == 'memory_intensive':
            self.config.update({
                'chunk_size': 500,
                'max_workers': max(2, mp.cpu_count() // 2),
                'cache_ttl': 1800,  # 30 minutos
                'memory_threshold': 0.7
            })
        
        elif workload_profile == 'cpu_intensive':
            self.config.update({
                'chunk_size': 2000,
                'max_workers': mp.cpu_count(),
                'cache_ttl': 7200,  # 2 horas
                'memory_threshold': 0.9
            })
        
        elif workload_profile == 'io_intensive':
            self.config.update({
                'chunk_size': 1500,
                'max_workers': min(mp.cpu_count() * 2, 16),
                'cache_ttl': 3600,  # 1 hora
                'memory_threshold': 0.8
            })
        
        self.logger.info(f"Configuração otimizada para perfil: {workload_profile}")
    
    @profile
    def memory_profile_operation(self, operation: Callable, *args, **kwargs) -> Any:
        """Executa operação com profiling de memória"""
        return operation(*args, **kwargs)

# Decorador para cache automático
def cached_operation(ttl: int = 3600):
    """Decorador para cache automático de operações"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Gerar chave de cache
            cache_key = f"{func.__name__}_{hash(str(args) + str(kwargs))}"
            
            # Tentar recuperar do cache
            # (implementação simplificada - em produção usar OptimizationService)
            
            # Executar função
            result = func(*args, **kwargs)
            
            # Salvar no cache
            # (implementação do cache)
            
            return result
        return wrapper
    return decorator

# Exemplo de uso do decorador
@cached_operation(ttl=1800)
def expensive_calculation(data: pd.DataFrame) -> pd.DataFrame:
    """Exemplo de operação cara que se beneficia de cache"""
    # Simulação de operação pesada
    time.sleep(0.1)
    return data.groupby('categoria').agg({'valor': 'sum'})