/****** Object:  Table [Final].[Accounts]    Script Date: 2/25/2026 2:57:02 PM ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

CREATE TABLE [Final].[Accounts](
	[AccountID] [int] NOT NULL,
	[AccountName] [nvarchar](255) NOT NULL,
	[StatementType] [nvarchar](100) NOT NULL,
	[IsCalculated] [tinyint] NOT NULL,
	[DivisorAccountID] [int] NOT NULL,
	[DisplayOrder] [int] NOT NULL,
PRIMARY KEY CLUSTERED 
(
	[AccountID] ASC
)WITH (STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO

