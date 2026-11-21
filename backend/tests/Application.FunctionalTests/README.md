# Застарілий шаблон тестів

Приклади TodoItems/TodoLists належали початковому шаблону та не входили до
`Masters.Api.sln`. Їх вилучено: вони не перевіряли паркувальну систему і не
збиралися після зміни предметної області.

Актуальні перевірки API, доступу, телеметрії, читання даних та бази розміщено
в `../Application.UnitTests/`. Вебтести використовують окрему базу з випадковою
назвою й перевіряють її ідентичність перед очищенням.

З кореня репозиторію:

```powershell
dotnet test backend/tests/Application.UnitTests/Application.UnitTests.csproj -tl /p:UseArtifactsOutput=false
```
