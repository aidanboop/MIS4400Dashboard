/****** Object:  Table [Final].[AccountCalc]    Script Date: 2/25/2026 2:56:44 PM ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

CREATE TABLE [Final].[AccountCalc](
	[DestAccountID] [int] NOT NULL,
	[SeqID] [int] NOT NULL,
	[SourceAccountID] [int] NULL,
	[Multiplier] [decimal](15, 4) NOT NULL,
PRIMARY KEY CLUSTERED 
(
	[DestAccountID] ASC,
	[SeqID] ASC
)WITH (STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO

ALTER TABLE [Final].[AccountCalc]  WITH CHECK ADD FOREIGN KEY([DestAccountID])
REFERENCES [Final].[Accounts] ([AccountID])
GO

ALTER TABLE [Final].[AccountCalc]  WITH CHECK ADD FOREIGN KEY([SourceAccountID])
REFERENCES [Final].[Accounts] ([AccountID])
GO

