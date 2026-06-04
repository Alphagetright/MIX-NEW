# -*- coding: utf-8 -*-
"""异常体系 —— 分层异常定义，覆盖管线全生命周期"""


class PipelineError(Exception):
    """管线异常基类"""
    code = 1000

    def __init__(self, message, cause=None, context=None):
        super().__init__(message)
        self.message = message
        self.cause = cause
        self.context = context or {}

    def to_dict(self):
        return {
            "code": self.code,
            "message": self.message,
            "cause": str(self.cause) if self.cause else None,
            "context": self.context,
        }


class InputError(PipelineError):
    """输入异常：文件读取、编码检测、格式识别失败"""
    code = 2000


class EncodingError(InputError):
    """编码检测/转换异常"""
    code = 2010


class FormatError(InputError):
    """格式识别/解析异常"""
    code = 2020


class ParseError(PipelineError):
    """解析异常：AI输出解析、JSON提取、字段映射失败"""
    code = 3000


class JSONExtractError(ParseError):
    """JSON提取异常"""
    code = 3010


class JSONRepairError(ParseError):
    """JSON修复异常"""
    code = 3020


class FieldMappingError(ParseError):
    """字段映射异常"""
    code = 3030


class ValidateError(PipelineError):
    """校验异常：数据校验、类型检查、交叉校验失败"""
    code = 4000


class SchemaError(ValidateError):
    """Schema定义/校验异常"""
    code = 4010


class TypeCheckError(ValidateError):
    """类型检查异常"""
    code = 4020


class CrossValidateError(ValidateError):
    """交叉校验异常"""
    code = 4030


class GenerateError(PipelineError):
    """生成异常：模板加载、推理调用、结果收集失败"""
    code = 5000


class TemplateError(GenerateError):
    """模板加载/渲染异常"""
    code = 5010


class InferenceError(GenerateError):
    """推理调用异常"""
    code = 5020


class RetryExhaustedError(GenerateError):
    """重试耗尽异常"""
    code = 5030


class OutputError(PipelineError):
    """输出异常：序列化、写入、归档失败"""
    code = 6000


class SerializeError(OutputError):
    """序列化异常"""
    code = 6010


class WriteError(OutputError):
    """写入异常"""
    code = 6020


class ConfigError(PipelineError):
    """配置异常：配置加载、校验、监视失败"""
    code = 7000


class ConfigLoadError(ConfigError):
    """配置加载异常"""
    code = 7010


class ConfigValidateError(ConfigError):
    """配置校验异常"""
    code = 7020


class CacheError(PipelineError):
    """缓存异常：缓存读写、淘汰、持久化失败"""
    code = 8000


class RetryError(PipelineError):
    """重试/熔断异常"""
    code = 9000


class CircuitBreakerError(RetryError):
    """熔断器触发异常"""
    code = 9010


class LogError(PipelineError):
    """日志异常"""
    code = 10000


class PipelineBuildError(PipelineError):
    """管线构建异常"""
    code = 11000


class PipelineRunError(PipelineError):
    """管线运行异常"""
    code = 11010


ERROR_CODE_MAP = {
    2000: "InputError",
    2010: "EncodingError",
    2020: "FormatError",
    3000: "ParseError",
    3010: "JSONExtractError",
    3020: "JSONRepairError",
    3030: "FieldMappingError",
    4000: "ValidateError",
    4010: "SchemaError",
    4020: "TypeCheckError",
    4030: "CrossValidateError",
    5000: "GenerateError",
    5010: "TemplateError",
    5020: "InferenceError",
    5030: "RetryExhaustedError",
    6000: "OutputError",
    6010: "SerializeError",
    6020: "WriteError",
    7000: "ConfigError",
    7010: "ConfigLoadError",
    7020: "ConfigValidateError",
    8000: "CacheError",
    9000: "RetryError",
    9010: "CircuitBreakerError",
    10000: "LogError",
    11000: "PipelineBuildError",
    11010: "PipelineRunError",
}


def error_code_to_name(code):
    return ERROR_CODE_MAP.get(code, "UnknownError")
