namespace Masters.Api.Application.Common.Interfaces;

public interface IApplicationText
{
    string this[string key] { get; }

    string Format(string key, params object?[] args);
}
