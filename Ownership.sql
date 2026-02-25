/****** Object:  Table [Final].[Ownership]    Script Date: 2/25/2026 2:57:53 PM ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

CREATE TABLE [Final].[Ownership](
	[FranchiseeID] [int] NOT NULL,
	[StoreID] [int] NOT NULL,
	[StartDate] [int] NOT NULL,
	[EndDate] [int] NOT NULL,
PRIMARY KEY CLUSTERED 
(
	[FranchiseeID] ASC,
	[StoreID] ASC,
	[StartDate] ASC
)WITH (STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO

ALTER TABLE [Final].[Ownership]  WITH CHECK ADD FOREIGN KEY([FranchiseeID])
REFERENCES [Final].[Franchisees] ([FranchiseeID])
GO

ALTER TABLE [Final].[Ownership]  WITH CHECK ADD FOREIGN KEY([StoreID])
REFERENCES [Final].[Stores] ([StoreID])
GO

