/****** Object:  Table [Final].[POSSales]    Script Date: 2/25/2026 2:58:08 PM ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

CREATE TABLE [Final].[POSSales](
	[StoreID] [int] NOT NULL,
	[FiscalYearID] [int] NOT NULL,
	[CalendarID] [int] NOT NULL,
	[Sales] [money] NOT NULL,
PRIMARY KEY CLUSTERED 
(
	[StoreID] ASC,
	[FiscalYearID] ASC,
	[CalendarID] ASC
)WITH (STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO

ALTER TABLE [Final].[POSSales]  WITH CHECK ADD FOREIGN KEY([StoreID])
REFERENCES [Final].[Stores] ([StoreID])
GO

