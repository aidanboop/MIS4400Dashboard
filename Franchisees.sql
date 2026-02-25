/****** Object:  Table [Final].[Franchisees]    Script Date: 2/25/2026 2:57:22 PM ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

CREATE TABLE [Final].[Franchisees](
	[FranchiseeID] [int] NOT NULL,
	[FranchiseeName] [nvarchar](255) NOT NULL,
	[OrgID] [int] NOT NULL,
	[OrgName] [nvarchar](255) NOT NULL,
PRIMARY KEY CLUSTERED 
(
	[FranchiseeID] ASC
)WITH (STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO

