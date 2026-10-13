#include "PalGraphLib.h"

#include "Animation/AnimBlueprint.h"
#include "Animation/Skeleton.h"
#include "Animation/MorphTarget.h"
#include "AnimationGraph.h"
#include "AnimationGraphSchema.h"
#include "Engine/Blueprint.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/SkeletalMeshSocket.h"
#include "EdGraph/EdGraph.h"
#include "EdGraph/EdGraphNode.h"
#include "EdGraph/EdGraphPin.h"
#include "EdGraph/EdGraphSchema.h"
#include "EdGraphSchema_K2.h"
#include "EdGraphUtilities.h"
#include "Kismet2/BlueprintEditorUtils.h"
#include "Kismet2/KismetEditorUtilities.h"
#include "Kismet2/CompilerResultsLog.h"
#include "UObject/UnrealType.h"

namespace
{
	UBlueprint* OwningBlueprint(UObject* Obj)
	{
		for (UObject* It = Obj; It; It = It->GetOuter())
		{
			if (UBlueprint* BP = Cast<UBlueprint>(It))
			{
				return BP;
			}
		}
		return nullptr;
	}

	// Walks "A.B[3].C" through struct and array properties; arrays grow when bGrow.
	bool ResolvePath(UObject* Obj, const FString& Path, bool bGrow, FProperty*& OutProp, void*& OutPtr)
	{
		TArray<FString> Parts;
		Path.ParseIntoArray(Parts, TEXT("."));
		const UStruct* Struct = Obj->GetClass();
		void* Container = Obj;
		for (int32 i = 0; i < Parts.Num(); ++i)
		{
			FString Name = Parts[i];
			int32 Index = INDEX_NONE;
			int32 Bracket;
			if (Name.FindChar(TEXT('['), Bracket))
			{
				Index = FCString::Atoi(*Name.Mid(Bracket + 1));
				Name = Name.Left(Bracket);
			}
			FProperty* Prop = FindFProperty<FProperty>(Struct, FName(*Name));
			if (!Prop)
			{
				UE_LOG(LogTemp, Warning, TEXT("[PalGraphLib] no property '%s' in %s"), *Name, *Struct->GetName());
				return false;
			}
			void* ValuePtr = Prop->ContainerPtrToValuePtr<void>(Container);
			if (Index != INDEX_NONE)
			{
				FArrayProperty* ArrayProp = CastField<FArrayProperty>(Prop);
				if (!ArrayProp)
				{
					return false;
				}
				FScriptArrayHelper Helper(ArrayProp, ValuePtr);
				if (Index >= Helper.Num())
				{
					if (!bGrow)
					{
						return false;
					}
					Helper.AddValues(Index + 1 - Helper.Num());
				}
				ValuePtr = Helper.GetRawPtr(Index);
				Prop = ArrayProp->Inner;
			}
			if (i == Parts.Num() - 1)
			{
				OutProp = Prop;
				OutPtr = ValuePtr;
				return true;
			}
			FStructProperty* StructProp = CastField<FStructProperty>(Prop);
			if (!StructProp)
			{
				return false;
			}
			Struct = StructProp->Struct;
			Container = ValuePtr;
		}
		return false;
	}

	TArray<FString> DumpRef(const FReferenceSkeleton& Ref)
	{
		TArray<FString> Out;
		const TArray<FTransform>& Pose = Ref.GetRefBonePose();
		for (int32 i = 0; i < Ref.GetNum(); ++i)
		{
			const FVector T = Pose[i].GetLocation();
			const FQuat Q = Pose[i].GetRotation();
			const int32 Parent = Ref.GetParentIndex(i);
			Out.Add(FString::Printf(TEXT("%s|%s|%f %f %f|%f %f %f %f"), *Ref.GetBoneName(i).ToString(),
				Parent == INDEX_NONE ? TEXT("") : *Ref.GetBoneName(Parent).ToString(), T.X, T.Y, T.Z, Q.X, Q.Y, Q.Z, Q.W));
		}
		return Out;
	}
}

UObject* UPalGraphLib::GetGraph(UBlueprint* Blueprint, const FString& GraphName)
{
	if (!Blueprint)
	{
		return nullptr;
	}
	TArray<UEdGraph*> Graphs;
	Blueprint->GetAllGraphs(Graphs);
	for (UEdGraph* Graph : Graphs)
	{
		if (Graph && Graph->GetName() == GraphName)
		{
			return Graph;
		}
	}
	return nullptr;
}

TArray<FString> UPalGraphLib::ListGraphs(UBlueprint* Blueprint)
{
	TArray<FString> Out;
	if (Blueprint)
	{
		TArray<UEdGraph*> Graphs;
		Blueprint->GetAllGraphs(Graphs);
		for (UEdGraph* Graph : Graphs)
		{
			if (Graph)
			{
				Out.Add(FString::Printf(TEXT("%s|%s|nodes=%d"), *Graph->GetName(), *Graph->GetClass()->GetName(), Graph->Nodes.Num()));
			}
		}
	}
	return Out;
}

TArray<UObject*> UPalGraphLib::GetNodes(UObject* Graph)
{
	TArray<UObject*> Out;
	if (UEdGraph* G = Cast<UEdGraph>(Graph))
	{
		for (UEdGraphNode* Node : G->Nodes)
		{
			Out.Add(Node);
		}
	}
	return Out;
}

UObject* UPalGraphLib::AddNode(UObject* Graph, const FString& NodeClassPath, int32 X, int32 Y)
{
	UEdGraph* G = Cast<UEdGraph>(Graph);
	UClass* NodeClass = LoadObject<UClass>(nullptr, *NodeClassPath);
	if (!G || !NodeClass || !NodeClass->IsChildOf(UEdGraphNode::StaticClass()))
	{
		UE_LOG(LogTemp, Warning, TEXT("[PalGraphLib] AddNode: bad graph or class '%s'"), *NodeClassPath);
		return nullptr;
	}
	G->Modify();
	UEdGraphNode* Node = NewObject<UEdGraphNode>(G, NodeClass, NAME_None, RF_Transactional);
	G->AddNode(Node, false, false);
	Node->CreateNewGuid();
	Node->PostPlacedNewNode();
	Node->AllocateDefaultPins();
	Node->NodePosX = X;
	Node->NodePosY = Y;
	if (UBlueprint* BP = OwningBlueprint(G))
	{
		FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(BP);
	}
	return Node;
}

bool UPalGraphLib::RemoveNode(UObject* Node)
{
	UEdGraphNode* N = Cast<UEdGraphNode>(Node);
	UBlueprint* BP = OwningBlueprint(Node);
	if (!N || !BP)
	{
		return false;
	}
	FBlueprintEditorUtils::RemoveNode(BP, N, true);
	return true;
}

TArray<FString> UPalGraphLib::GetPins(UObject* Node)
{
	TArray<FString> Out;
	if (UEdGraphNode* N = Cast<UEdGraphNode>(Node))
	{
		for (UEdGraphPin* Pin : N->Pins)
		{
			Out.Add(FString::Printf(TEXT("%s %s %s links=%d hidden=%d default=%s"),
				Pin->Direction == EGPD_Input ? TEXT("IN") : TEXT("OUT"),
				*Pin->PinName.ToString(), *Pin->PinType.PinCategory.ToString(),
				Pin->LinkedTo.Num(), Pin->bHidden ? 1 : 0, *Pin->DefaultValue));
		}
	}
	return Out;
}

FString UPalGraphLib::Connect(UObject* FromNode, const FString& FromPin, UObject* ToNode, const FString& ToPin)
{
	UEdGraphNode* A = Cast<UEdGraphNode>(FromNode);
	UEdGraphNode* B = Cast<UEdGraphNode>(ToNode);
	if (!A || !B)
	{
		return TEXT("FAIL bad nodes");
	}
	UEdGraphPin* Out = A->FindPin(FName(*FromPin), EGPD_Output);
	UEdGraphPin* In = B->FindPin(FName(*ToPin), EGPD_Input);
	if (!Out || !In)
	{
		return FString::Printf(TEXT("FAIL missing pin out=%d in=%d"), Out ? 1 : 0, In ? 1 : 0);
	}
	const UEdGraphSchema* Schema = Out->GetSchema();
	const FPinConnectionResponse Response = Schema->CanCreateConnection(Out, In);
	const bool bOk = Schema->TryCreateConnection(Out, In);
	if (UBlueprint* BP = OwningBlueprint(A))
	{
		FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(BP);
	}
	return FString::Printf(TEXT("%s response=%d %s"), bOk ? TEXT("OK") : TEXT("FAIL"), (int32)Response.Response.GetValue(), *Response.Message.ToString());
}

bool UPalGraphLib::SetPinDefault(UObject* Node, const FString& PinName, const FString& Value)
{
	UEdGraphNode* N = Cast<UEdGraphNode>(Node);
	UEdGraphPin* Pin = N ? N->FindPin(FName(*PinName), EGPD_Input) : nullptr;
	if (!Pin)
	{
		return false;
	}
	N->Modify();
	Pin->GetSchema()->TrySetDefaultValue(*Pin, Value);
	return true;
}

bool UPalGraphLib::SetProperty(UObject* Object, const FString& Path, const FString& Value)
{
	if (!Object)
	{
		return false;
	}
	Object->Modify();
	FProperty* Prop = nullptr;
	void* Ptr = nullptr;
	if (!ResolvePath(Object, Path, true, Prop, Ptr))
	{
		return false;
	}
	const TCHAR* Result = Prop->ImportText_Direct(*Value, Ptr, Object, PPF_None);
	if (!Result)
	{
		UE_LOG(LogTemp, Warning, TEXT("[PalGraphLib] ImportText failed for %s = %s"), *Path, *Value);
	}
	return Result != nullptr;
}

FString UPalGraphLib::GetProperty(UObject* Object, const FString& Path)
{
	FProperty* Prop = nullptr;
	void* Ptr = nullptr;
	if (!Object || !ResolvePath(Object, Path, false, Prop, Ptr))
	{
		return TEXT("<unresolved>");
	}
	FString Out;
	Prop->ExportTextItem_Direct(Out, Ptr, nullptr, Object, PPF_None);
	return Out;
}

void UPalGraphLib::Reconstruct(UObject* Node)
{
	if (UEdGraphNode* N = Cast<UEdGraphNode>(Node))
	{
		N->Modify();
		N->ReconstructNode();
		if (UBlueprint* BP = OwningBlueprint(N))
		{
			FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(BP);
		}
	}
}

bool UPalGraphLib::AddVariable(UBlueprint* Blueprint, FName Name, FName PinCategory, bool bInstanceEditable, const FString& DefaultValue)
{
	if (!Blueprint)
	{
		return false;
	}
	FEdGraphPinType PinType;
	PinType.PinCategory = PinCategory;
	if (!FBlueprintEditorUtils::AddMemberVariable(Blueprint, Name, PinType, DefaultValue))
	{
		return false;
	}
	FBlueprintEditorUtils::SetBlueprintOnlyEditableFlag(Blueprint, Name, !bInstanceEditable);
	return true;
}

bool UPalGraphLib::ImplementInterface(UBlueprint* Blueprint, const FString& InterfaceClassPath)
{
	if (!Blueprint)
	{
		return false;
	}
	UClass* Interface = LoadObject<UClass>(nullptr, *InterfaceClassPath);
	if (!Interface)
	{
		UE_LOG(LogTemp, Warning, TEXT("[PalGraphLib] ImplementInterface: cannot load %s"), *InterfaceClassPath);
		return false;
	}
	const bool bOk = FBlueprintEditorUtils::ImplementNewInterface(Blueprint, Interface->GetClassPathName());
	FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(Blueprint);
	return bOk;
}

UObject* UPalGraphLib::AddAnimLayerGraph(UBlueprint* Blueprint, FName LayerName)
{
	if (!Blueprint)
	{
		return nullptr;
	}
	UEdGraph* Graph = FBlueprintEditorUtils::CreateNewGraph(Blueprint, LayerName, UAnimationGraph::StaticClass(), UAnimationGraphSchema::StaticClass());
	// same as FBlueprintEditor::NewDocument_OnClicked(CGT_NewAnimationLayer) (AddFunctionGraph asserts on anim graphs)
	FBlueprintEditorUtils::AddDomainSpecificGraph(Blueprint, Graph);
	FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(Blueprint);
	return Graph;
}

FString UPalGraphLib::Compile(UBlueprint* Blueprint)
{
	if (!Blueprint)
	{
		return TEXT("status=-1 no blueprint");
	}
	FCompilerResultsLog Log;
	FKismetEditorUtilities::CompileBlueprint(Blueprint, EBlueprintCompileOptions::None, &Log);
	FString Out = FString::Printf(TEXT("status=%d errors=%d warnings=%d"), (int32)Blueprint->Status, Log.NumErrors, Log.NumWarnings);
	for (const TSharedRef<FTokenizedMessage>& Message : Log.Messages)
	{
		Out += TEXT("\n  ") + Message->ToText().ToString();
	}
	return Out;
}

FString UPalGraphLib::ExportGraph(UObject* Graph)
{
	FString Out;
	if (UEdGraph* G = Cast<UEdGraph>(Graph))
	{
		TSet<UObject*> Nodes;
		for (UEdGraphNode* Node : G->Nodes)
		{
			Nodes.Add(Node);
		}
		FEdGraphUtilities::ExportNodesToText(Nodes, Out);
	}
	return Out;
}

TArray<FString> UPalGraphLib::GetRefPose(USkeletalMesh* Mesh)
{
	return Mesh ? DumpRef(Mesh->GetRefSkeleton()) : TArray<FString>();
}

TArray<FString> UPalGraphLib::GetSkeletonRefPose(USkeleton* Skeleton)
{
	return Skeleton ? DumpRef(Skeleton->GetReferenceSkeleton()) : TArray<FString>();
}

bool UPalGraphLib::SetMeshSkeleton(USkeletalMesh* Mesh, USkeleton* Skeleton)
{
	if (!Mesh || !Skeleton)
	{
		return false;
	}
	Mesh->Modify();
	Mesh->SetSkeleton(Skeleton);
	Mesh->MarkPackageDirty();
	return true;
}

bool UPalGraphLib::SetMeshSocket(USkeletalMesh* Mesh, FName SocketName, FName BoneName, FVector Location, FRotator Rotation, FVector Scale)
{
	if (!Mesh)
	{
		return false;
	}
	Mesh->Modify();
	USkeletalMeshSocket* Socket = Mesh->FindSocket(SocketName);
	if (!Socket)
	{
		Socket = NewObject<USkeletalMeshSocket>(Mesh);
		Socket->SocketName = SocketName;
		Mesh->GetMeshOnlySocketList().Add(Socket);
	}
	Socket->BoneName = BoneName;
	Socket->RelativeLocation = Location;
	Socket->RelativeRotation = Rotation;
	Socket->RelativeScale = Scale;
	Mesh->MarkPackageDirty();
	return true;
}

TArray<FString> UPalGraphLib::GetMorphTargets(USkeletalMesh* Mesh)
{
	TArray<FString> Out;
	if (Mesh)
	{
		for (UMorphTarget* M : Mesh->GetMorphTargets())
		{
			if (M)
			{
				int32 N = 0;
				for (const FMorphTargetLODModel& L : M->GetMorphLODModels())
				{
					N += L.Vertices.Num();
				}
				Out.Add(FString::Printf(TEXT("%s|%d"), *M->GetName(), N));
			}
		}
	}
	return Out;
}
