/****** Object:  Table [Final].[MainData]    Script Date: 2/25/2026 2:57:39 PM ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

CREATE TABLE [Final].[MainData](
	[FranchiseeID] [int] NOT NULL,
	[StoreID] [int] NOT NULL,
	[FiscalYearID] [int] NOT NULL,
	[CalendarID] [int] NOT NULL,
	[AccountID] [int] NOT NULL,
	[Amount] [money] NOT NULL,
PRIMARY KEY CLUSTERED 
(
	[FranchiseeID] ASC,
	[StoreID] ASC,
	[FiscalYearID] ASC,
	[CalendarID] ASC,
	[AccountID] ASC
)WITH (STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO

ALTER TABLE [Final].[MainData]  WITH CHECK ADD FOREIGN KEY([AccountID])
REFERENCES [Final].[Accounts] ([AccountID])
GO

ALTER TABLE [Final].[MainData]  WITH CHECK ADD FOREIGN KEY([FranchiseeID])
REFERENCES [Final].[Franchisees] ([FranchiseeID])
GO

ALTER TABLE [Final].[MainData]  WITH CHECK ADD FOREIGN KEY([StoreID])
REFERENCES [Final].[Stores] ([StoreID])
GO

