using Masters.Api.Application.Common.Exceptions;
using NUnit.Framework;
using Shouldly;

namespace Masters.Api.Application.UnitTests.Common.Exceptions;

public class ValidationExceptionTests
{
    [Test]
    public void DefaultConstructorCreatesAnEmptyErrorDictionary()
    {
        var actual = new ValidationException().Errors;

        actual.Keys.ShouldBeEmpty();
    }
}
