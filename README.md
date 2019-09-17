# modeltest-lambda

## Descrição

Neste projeto ficam os executáveis de fato, o código que roda na plataforma de computação em nuvem, no caso a AWS. 

Importante destacar que o código fonte é um só, mas ele é utilizado tanto para rodar no modo "serverless" (camada de **curta** duração) quando no modo "containers" (camada de **longa** duração). 

A principal diferença entre eles é que no caso da execução em containers é utilizado o projeto _Docker_ e isso exige um pouco mais de código pra fazer o setup/bootstrapping da implementação.


## Estrutura

- a pasta ``benchmark-phyles`` contém os arquivos de argumento (sob os quais rodam as análises) do jModelTest2, mantidos ali por conveniência;
- a pasta ``lib`` contém algumas dependências, sendo a principal delas o proejto phyml compilado para executar no ambiente do AWS Lambda e nos containeres;
- a pasta ``samples`` contém exemplos de arquivos recebidos pelos eventos durante a execução, utilizados para testes;
- a pasta ``src`` contém os fontes que basicamente fazem o trabalho de detectar o ambiente em que estão executando e parsear as mensagens/eventos recebidas pela infraestrutura e prosseguir com a execução traduzindo os parâmetros para um formato que o phyml reconheça. Além disso monitoram a execução, capturando e salvando os resultados em um espaço de armazenamento compartilhado (AWS S3);
- o arquivo ``Dockerfile`` é responsável por montar/compilar o container que será utilizado em runtime;
- o arquivo ``serverless.yml`` é a representação em código da infraestrutura necessária para disponibilizar um ambiente de computação em nuvem na plataforma da AWS para execução deste projeto, declarando o ambiente compartilhado de armazenamento (AWS S3), as funções "serverless" (AWS Lambda) e o orquestrador de containeres (AWS Batch) assim como a camada de comunicação gerenciada através de filas de mensagens (AWS SNS);
